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
                           default_route, remove_default,  remove_destination_networks,
                           remove_exit_interfaces_or_next_hops):
    try:
        device_info = device["device_info"]
        device_info['timeout'] = 10 
        net_connect = ConnectHandler(**device_info)
        net_connect.enable()

        config_commands = []
        for destination, exit_interface in zip(destination_networks, exit_interfaces_or_next_hops):
            if '/' in destination:  
                destination_ip, cidr = destination.split('/')
                subnet_mask = convert_cidr_to_netmask(cidr)  # แปลงเป็น subnet mask โดยใช้ cidr
                command = f"ip route {destination_ip} {subnet_mask} {exit_interface}"
                config_commands.append(command)

        if config_commands:
            output = net_connect.send_config_set(config_commands)
            print(f"Static Route Configuration for {device['name']}:", output)
        
        if default_route:
            if remove_default:  
                output = net_connect.send_config_set([f"no ip route 0.0.0.0 0.0.0.0 {default_route}"])
                print(f"Removed Default Route on {device['name']}:", output)
            else:
                output = net_connect.send_config_set([f"ip route 0.0.0.0 0.0.0.0 {default_route}"])
                print(f"Added Default Route on {device['name']}:", output)
        
        if remove_default:
            output = net_connect.send_config_set([f"no ip route 0.0.0.0 0.0.0.0"])
            print(f"Removed Default Route on {device['name']}:", output)
        
        if remove_destination_networks and remove_exit_interfaces_or_next_hops:
            for remove_destination, remove_exit_interface in zip(remove_destination_networks, remove_exit_interfaces_or_next_hops):
                if '/' in remove_destination:  
                    remove_destination_ip, remove_cidr = remove_destination.split('/')
                    remove_subnet_mask = convert_cidr_to_netmask(remove_cidr) 
                    command = f"no ip route {remove_destination_ip} {remove_subnet_mask} {remove_exit_interface}"
                    output = net_connect.send_config_set([command])
                    print(f"Removed Static Route on {device['name']}:", output)
        net_connect.disconnect()

    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        print(f"Error configuring static route on {device['name']}: {e}")
