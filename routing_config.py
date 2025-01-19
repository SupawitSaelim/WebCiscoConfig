from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException

def convert_cidr_to_netmask(cidr):
    print(f"cidr = {cidr}")  # ตรวจสอบค่าที่เข้ามา

    if '/' in cidr:
        ip, bits = cidr.split('/')  # แยก IP และ CIDR
        bits = int(bits)  
    else:
        bits = int(cidr)

    netmask = []
    for i in range(4):
        if bits >= 8:
            netmask.append(255)
            bits -= 8
        else:
            netmask.append(256 - 2**(8 - bits))  # คำนวณ subnet mask ที่เหลือ
            bits = 0
    return '.'.join(map(str, netmask))


def configure_static_route(device, destination_networks, exit_interfaces_or_next_hops, 
                         default_route, remove_default, remove_destination_networks,
                         remove_exit_interfaces_or_next_hops):
    """
    Configure static routes on a device with proper error handling
    """
    net_connect = None
    try:
        device_info = device["device_info"]
        device_info['timeout'] = 10
        net_connect = ConnectHandler(**device_info)
        net_connect.enable()

        # Configure static routes
        if destination_networks and exit_interfaces_or_next_hops:
            config_commands = []
            for destination, exit_interface in zip(destination_networks, exit_interfaces_or_next_hops):
                if '/' in destination:
                    destination_ip, cidr = destination.split('/')
                    subnet_mask = convert_cidr_to_netmask(cidr)
                    command = f"ip route {destination_ip} {subnet_mask} {exit_interface}"
                    config_commands.append(command)

            if config_commands:
                output = net_connect.send_config_set(config_commands)
                print(output)
        
        # Handle default route
        if default_route or remove_default:
            if remove_default:
                if default_route:
                    output = net_connect.send_config_set([f"no ip route 0.0.0.0 0.0.0.0 {default_route}"])
                    print(output)
                else:
                    output = net_connect.send_config_set(["no ip route 0.0.0.0 0.0.0.0"])
                    print(output)
            elif default_route:
                output = net_connect.send_config_set([f"ip route 0.0.0.0 0.0.0.0 {default_route}"])
                print(output)
        
        # Remove specific routes
        if remove_destination_networks and remove_exit_interfaces_or_next_hops:
            remove_commands = []
            for remove_destination, remove_exit_interface in zip(remove_destination_networks, remove_exit_interfaces_or_next_hops):
                if '/' in remove_destination:
                    remove_destination_ip, remove_cidr = remove_destination.split('/')
                    remove_subnet_mask = convert_cidr_to_netmask(remove_cidr)
                    command = f"no ip route {remove_destination_ip} {remove_subnet_mask} {remove_exit_interface}"
                    remove_commands.append(command)

            if remove_commands:
                output = net_connect.send_config_set(remove_commands)
                print(output)

        net_connect.disconnect()

    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        raise e
    except Exception as e:
        raise Exception(f"Error configuring static route: {str(e)}")


def configure_rip_route(device, destination_networks, auto_summary,
                       remove_destination_networks, disable_rip):
    """
    Configure RIP routing on a device with proper error handling
    """
    net_connect = None
    try:
        device_info = device["device_info"]
        device_info['timeout'] = 10
        net_connect = ConnectHandler(**device_info)
        net_connect.enable()

        if disable_rip:
            output = net_connect.send_config_set(["no router rip"])
            print(output)
        else:
            # Base RIP configuration
            config_commands = [
                'ip routing',
                'router rip',
                'version 2'
            ]

            # Add networks
            if destination_networks:
                valid_networks = [net.strip() for net in destination_networks if net.strip()]
                for network in valid_networks:
                    config_commands.append(f"network {network}")

            # Configure auto-summary
            if auto_summary == "Enable":
                config_commands.append("auto-summary")
            elif auto_summary == "Disable":
                config_commands.append("no auto-summary")

            # Remove networks
            if remove_destination_networks:
                valid_remove_networks = [net.strip() for net in remove_destination_networks if net.strip()]
                for network in valid_remove_networks:
                    config_commands.append(f"no network {network}")

            # Apply configuration if we have more than just the base commands
            if len(config_commands) > 3:
                output = net_connect.send_config_set(config_commands)
                print(output)

        net_connect.disconnect()

    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        raise e
    except Exception as e:
        raise Exception(f"Error configuring RIP: {str(e)}")


def configure_ospf_route(device, process_id, destination_networks, ospf_areas, router_id, 
                        remove_destination_networks, remove_ospf_areas, delete_process_id, 
                        process_id_input):
    try:
        device_info = device["device_info"]
        device_info['timeout'] = 10 
        net_connect = ConnectHandler(**device_info)
        net_connect.enable()

        # Combine all OSPF configuration commands
        config_commands = ['ip routing']
        if process_id:
            config_commands.append(f"router ospf {process_id}")
            # Add router-id configuration in the same command set
            if router_id:
                config_commands.append(f"router-id {router_id}")
            
            # Add network configurations
            if destination_networks and ospf_areas:
                for network, area in zip(destination_networks, ospf_areas):
                    if network.strip() and area.strip():
                        if '/' in network:  
                            network_ip, cidr = network.split('/')
                            subnet_mask = convert_cidr_to_netmask(cidr)
                            command = f"network {network_ip} {subnet_mask} area {area}"
                            config_commands.append(command)

        # Execute all OSPF configurations at once if there are commands
        if len(config_commands) > 1:
            output = net_connect.send_config_set(config_commands)
            print(f"OSPF Configuration for {device['name']}:", output)

        # Remove Part
        if remove_destination_networks and remove_ospf_areas and process_id:
            config_commands_remove = [f"router ospf {process_id}"]
            for network, area in zip(remove_destination_networks, remove_ospf_areas):
                if network.strip() and area.strip():
                    if '/' in network:
                        network_ip, cidr = network.split('/')
                        subnet_mask = convert_cidr_to_netmask(cidr)
                        command = f"no network {network_ip} {subnet_mask} area {area}"
                        config_commands_remove.append(command)

            if len(config_commands_remove) > 1:
                output = net_connect.send_config_set(config_commands_remove)
                print(f"OSPF Configuration for {device['name']}:", output)

        if delete_process_id and process_id_input:
            process_ids = process_id_input.split(',')
            for process_id in process_ids:
                process_id = process_id.strip() 
                output = net_connect.send_config_set(f"no router ospf {process_id}")
                print(f"OSPF Configuration for {device['name']} (Process ID: {process_id}):", output)

        net_connect.disconnect()

    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        raise e
    except Exception as e:
        raise Exception(f"Error configuring OSPF: {str(e)}")


def configure_eigrp_route(device, process_id, router_id, destination_networks, 
                          remove_destination_networks, delete_process_id, 
                          process_id_input):
    try:
        device_info = device["device_info"]
        device_info['timeout'] = 10
        net_connect = ConnectHandler(**device_info)
        net_connect.enable()

        config_commands = ['ip routing']
        if process_id:
            config_commands.append(f"router eigrp {process_id}")

        # Add networks
        if destination_networks and process_id:
            for network in destination_networks:
                if network.strip():
                    if '/' in network:  # Check if it's in CIDR format
                        network_ip, cidr = network.split('/')
                        subnet_mask = convert_cidr_to_netmask(cidr)
                        command = f"network {network_ip} {subnet_mask}"
                        config_commands.append(command)
                    else:
                        config_commands.append(f"network {network.strip()}")  # Assume subnet mask is included

        if len(config_commands) > 2:
            output = net_connect.send_config_set(config_commands)
            print(f"EIGRP Configuration for {device['name']}:", output)
            if "Invalid input detected" in output or "Incomplete command" in output:
                raise Exception(f"Configuration error: {output}")
        
        if router_id and process_id:
            output = net_connect.send_config_set([f"router eigrp {process_id}",f"router-id {router_id}"])
            print(f"EIGRP Configuration for {device['name']}:", output)
            if "Invalid input detected" in output or "Incomplete command" in output:
                raise Exception(f"Configuration error: {output}")

        # Remove networks
        config_commands_remove = []
        if remove_destination_networks and process_id:
            config_commands_remove.append(f"router eigrp {process_id}")
            for network in remove_destination_networks:
                if network.strip():
                    if '/' in network:  # Check if it's in CIDR format
                        network_ip, cidr = network.split('/')
                        subnet_mask = convert_cidr_to_netmask(cidr)
                        command = f"no network {network_ip} {subnet_mask}"
                        config_commands_remove.append(command)
                    else:
                        config_commands_remove.append(f"no network {network.strip()}")  # Assume subnet mask is included

        if len(config_commands_remove) > 1:
            output = net_connect.send_config_set(config_commands_remove)
            print(f"EIGRP Configuration for {device['name']}:", output)
            if "Invalid input detected" in output or "Incomplete command" in output:
                raise Exception(f"Configuration error: {output}")

        # Delete Process ID
        if delete_process_id and process_id_input:
            process_ids = process_id_input.split(',')
            for process_id in process_ids:
                process_id = process_id.strip()
                output = net_connect.send_config_set(f"no router eigrp {process_id}")
                print(f"EIGRP Configuration for {device['name']} (Process ID: {process_id}):", output)
                if "Invalid input detected" in output or "Incomplete command" in output:
                    raise Exception(f"Configuration error: {output}")

        net_connect.disconnect()

    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        raise e
    except Exception as e:
        raise Exception(f"Error configuring RIP: {str(e)}")

