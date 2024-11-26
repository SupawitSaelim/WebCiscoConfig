from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException
from pymongo import MongoClient
from bson import ObjectId

def configure_device(device, hostname, secret_password, banner, device_collection):
    device_info = device["device_info"]
    
    try:
        net_connect = ConnectHandler(**device_info)
        net_connect.enable()

        if hostname:
            output = net_connect.send_config_set([f'hostname {hostname}'])
            print(f"Hostname output for {device['name']}:", output)
            device_collection.update_one({"_id": ObjectId(device["_id"])}, {"$set": {"name": hostname}})
            net_connect.set_base_prompt()
        
        if secret_password:
            output = net_connect.send_config_set([f'enable secret {secret_password}'])
            device_collection.update_one({"_id": ObjectId(device["_id"])}, {"$set": {"device_info.secret": secret_password}})
            print(f"Enable secret output for {device['name']}:", output)
        
        if banner:
            output = net_connect.send_config_set([f'banner motd # {banner} #'])
            print(f"Banner output for {device['name']}:", output)
        
        net_connect.disconnect()
    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        print(f"Error connecting to {device['name']}: {e}")
        return f'<script>alert("Error connecting to {device["name"]}: {str(e)}"); window.location.href="/basic_settings";</script>'


def configure_network_interface(device, interfaces_ipv4,dhcp_ipv4, ip_address_ipv4, subnet_mask_ipv4, 
                                enable_ipv4, disable_ipv4, delete_ipv4,
                                interfaces_ipv6,dhcp_ipv6, ip_address_ipv6, enable_ipv6, 
                                disable_ipv6, delete_ipv6, interfaces_du,speed_duplex, device_collection):
    device_info = device["device_info"]
    
    try:
        net_connect = ConnectHandler(**device_info)
        net_connect.enable()

        output = net_connect.send_config_set(["ipv6 unicast-routing"])
        print(f"IPv6 unicast-routing Config for {device['name']}:", output)

        if dhcp_ipv4:
            ipv4_config = "ip address dhcp"
            output = net_connect.send_config_set([f"interface range {interfaces_ipv4}", "no switchport", ipv4_config])
            print(f"IPv4 Config for {device['name']} (DHCP):", output)

        if ip_address_ipv4: 
            ipv4_config = f"ip address {ip_address_ipv4} {subnet_mask_ipv4}"
            output = net_connect.send_config_set([f"interface range {interfaces_ipv4}", "no switchport", ipv4_config])
            print(f"IPv4 Config for {device['name']}:", output)

        if enable_ipv4:
            output = net_connect.send_config_set([f"interface range {interfaces_ipv4}", "no shutdown"])
            print(f"IPv4 Config for {device['name']}:", output)
        
        if disable_ipv4:
            output = net_connect.send_config_set([f"interface range {interfaces_ipv4}", "shutdown"])
            print(f"Disable IPv4 for {device['name']}:", output)

        if delete_ipv4:
            output = net_connect.send_config_set([f"interface range {interfaces_ipv4}", "no ip address"])
            print(f"Delete IPv4 for {device['name']}:", output)


        if dhcp_ipv6:
            ipv6_config = "ipv6 address dhcp"
            output = net_connect.send_config_set([f"interface range {interfaces_ipv6}", "no switchport", ipv6_config])
            print(f"IPv4 Config for {device['name']} (DHCP):", output)

        if ip_address_ipv6: 
            ipv6_config = f"ipv6 address {ip_address_ipv6}"
            output = net_connect.send_config_set([f"interface range {interfaces_ipv6}", "no switchport", ipv6_config])
            print(f"IPv6 Config for {device['name']}:", output)

        if enable_ipv6:
            output = net_connect.send_config_set([f"interface range {interfaces_ipv6}", "no shutdown"])
            print(f"IPv6 Config for {device['name']}:", output)

        if disable_ipv6:
            output = net_connect.send_config_set([f"interface range {interfaces_ipv6}", "shutdown"])
            print(f"Disable IPv6 for {device['name']}:", output)

        if delete_ipv6:
            output = net_connect.send_config_set([f"interface range {interfaces_ipv6}", "no ipv6 address"])
            print(f"Delete IPv6 for {device['name']}:", output)

        if interfaces_du:
            output = net_connect.send_config_set([f"interface range {interfaces_du}", f"duplex {speed_duplex}"])
            print(f"Duplex Config for {device['name']}:", output)

        net_connect.disconnect()
    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        print(f"Error connecting to {device['name']}: {e}")
        return f'<script>alert("Error connecting to {device["name"]}: {str(e)}"); window.location.href="/network_interface_page";</script>'


def manage_vlan_on_device(device, vlan_range, vlan_range_del, vlan_changes, vlan_range_enable, vlan_range_disable,
                          access_vlans, access_interface, access_vlan_id, disable_dtp,
                          trunk_ports, trunk_mode_select, trunk_interface, trunk_native, allow_vlan):
    device_info = device["device_info"]

    try:
        net_connect = ConnectHandler(**device_info)
        net_connect.enable()

        for vlan_id in vlan_range:
            vlan_config_command = f"vlan {vlan_id}"
            output = net_connect.send_config_set([vlan_config_command])
            print(f"VLAN {vlan_id} creation output for {device['name']}:", output)

        for vlan_id in vlan_range_del:
            vlan_delete_command = f"no vlan {vlan_id}"
            output = net_connect.send_config_set([vlan_delete_command])
            print(f"VLAN {vlan_id} deletion output for {device['name']}:", output)
        
        if vlan_changes:
            for vlan_id, new_name in vlan_changes:
                if vlan_id and new_name:
                    vlan_rename_command1 = f"vlan {vlan_id}"
                    vlan_rename_command2 = f"name {new_name}"
                    output = net_connect.send_config_set([vlan_rename_command1, vlan_rename_command2])
                    print(f"VLAN {vlan_id} renamed to {new_name} on {device['name']}:", output)

        for vlan_id in vlan_range_enable:
            vlan_enable_command = f"vlan {vlan_id}"
            output = net_connect.send_config_set([vlan_enable_command,"no sh"])
            print(f"VLAN {vlan_id} enabled on {device['name']}:", output)

        for vlan_id in vlan_range_disable:
            vlan_disable_command = f"vlan {vlan_id}"
            output = net_connect.send_config_set([vlan_disable_command,"sh"])
            print(f"VLAN {vlan_id} disabled on {device['name']}:", output)

        if access_vlans and access_interface and access_vlan_id:
            access_config_commands = [
                f"interface range {access_interface}",
                f"switchport mode access",
                f"switchport access vlan {access_vlan_id}"
            ]
            if disable_dtp:
                access_config_commands.append("switchport nonegotiate")  # ปิด DTP
                output = net_connect.send_config_set(access_config_commands)
                print(f"Access VLAN configuration output for {device['name']}:", output)
            else :
                output = net_connect.send_config_set(access_config_commands)
                print(f"Access VLAN configuration output for {device['name']}:", output)

        if disable_dtp and access_interface:
                access_dtp_commands = ([f"interface range {access_interface}","switchport nonegotiate"])  # ปิด DTP
                output = net_connect.send_config_set(access_dtp_commands)
                print(f"Access VLAN configuration output for {device['name']}:", output)

        if trunk_ports and trunk_interface and trunk_mode_select:
            trunk_config_commands = [
                f"interface range {trunk_interface}",
                "switchport trunk encapsulation dot1q",
                "switchport mode trunk",
            ]
            if trunk_mode_select in ["auto", "desirable"]:
                trunk_config_commands.append("no switchport nonegotiate")
                trunk_config_commands.append(f"switchport mode dynamic {trunk_mode_select}")
            if trunk_native:
                trunk_config_commands.append(f'switchport trunk native vlan {trunk_native}')
            if allow_vlan:
                trunk_config_commands.append(f'sw tr allow vlan {allow_vlan}')
            output = net_connect.send_config_set(trunk_config_commands)
            print(f"Trunk Mode configuration output for {device['name']}:", output)



        net_connect.disconnect()

    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        print(f"Error connecting to {device['name']}: {e}")
        return f'<script>alert("Error connecting to {device["name"]}: {str(e)}"); window.location.href="/vlan_settings";</script>'



def configure_vty_console(device, password_vty, authen_method, exec_timeout_vty, login_method, logging_sync_vty, 
                          password_console, exec_timeout_console, logging_sync_console, authen_method_con,
                          pool_name, network, dhcp_subnet, dhcp_exclude, default_router, dns_server, domain_name,
                          ntp_server, time_zone_name, hour_offset, snmp_ro, snmp_rw, snmp_contact, snmp_location,
                          enable_cdp, disable_cdp, enable_lldp, disable_lldp):
    device_info = device["device_info"]

    try:
        net_connect = ConnectHandler(**device_info)
        net_connect.enable()

        vty_commands = ["line vty 0 4"]
        if password_vty:
            vty_commands.append(f"password {password_vty}")

        if authen_method:
            vty_commands.append(f"{authen_method}")

        if exec_timeout_vty:
            vty_commands.append(f"exec-timeout {exec_timeout_vty}")

        if login_method:
            if login_method.lower() in ["ssh", "telnet"]:
                vty_commands.append(f"transport input {login_method}")
            elif login_method.lower() == "none":
                vty_commands.append("transport input none")
            else:
                vty_commands.append("transport input all")

        if logging_sync_vty:
            vty_commands.append("loggin synchronous")

        if len(vty_commands) > 1:
            output = net_connect.send_config_set(vty_commands)
            print(f"VTY Configuration for {device['name']}:", output)

        console_commands = ["line console 0"]
        if password_console:
            console_commands.append(f"password {password_console}")
            console_commands.append("login")

        if exec_timeout_console:
            console_commands.append(f"exec-timeout {exec_timeout_console}")

        if logging_sync_console:
            console_commands.append("loggin synchronous")
        
        if authen_method_con:
            console_commands.append(f"{authen_method_con}")

        if len(console_commands) > 1:
            output = net_connect.send_config_set(console_commands)
            print(f"Console Configuration for {device['name']}:", output)

        dhcp_commands = []
        if pool_name:
            dhcp_commands.append(f"ip dhcp pool {pool_name}")
            if network and dhcp_subnet:
                dhcp_commands.append(f"network {network} {dhcp_subnet}")
            if default_router:
                dhcp_commands.append(f"default-router {default_router}")
            if dns_server:
                dhcp_commands.append(f"dns-server {dns_server}")
            if domain_name:
                dhcp_commands.append(f"domain-name {domain_name}")
        if dhcp_exclude:
            dhcp_exclude_list = dhcp_exclude.split(',')
            for exclude_range in dhcp_exclude_list:
                exclude_range = exclude_range.strip()
                if '-' in exclude_range:
                    start_ip, end_ip = exclude_range.split('-')
                    dhcp_commands.append(f"ip dhcp excluded-address {start_ip.strip()} {end_ip.strip()}")
                else:
                    dhcp_commands.append(f"ip dhcp excluded-address {exclude_range}")
        if dhcp_commands:
            output = net_connect.send_config_set(dhcp_commands)
            print(f"DHCP Configuration for {device['name']}:", output)
        
        if ntp_server:
            ntp_output = net_connect.send_config_set([f"ntp server {ntp_server}"])
            print(f"NTP Configuration for {device['name']}:", ntp_output)

        if time_zone_name and hour_offset:
            timezone_output = net_connect.send_config_set(f"clock timezone {time_zone_name} {hour_offset}")
            print(f"Time Zone Configuration for {device['name']}:", timezone_output)

        snmp_commands = []
        if snmp_ro:
            snmp_commands.append(f"snmp-server community {snmp_ro} RO")
        if snmp_rw:
            snmp_commands.append(f"snmp-server community {snmp_rw} RW")
        if snmp_contact:
            snmp_commands.append(f"snmp-server contact {snmp_contact}")
        if snmp_location:
            snmp_commands.append(f"snmp-server location {snmp_location}")
        
        if snmp_commands:
            output = net_connect.send_config_set(snmp_commands)
            print(f"SNMP Configuration for {device['name']}:", output)

        cdp_commands = []
        if enable_cdp:
            cdp_commands.append("cdp run")
        elif disable_cdp:
            cdp_commands.append("no cdp run")

        if cdp_commands:
            output = net_connect.send_config_set(cdp_commands)
            print(f"CDP Configuration for {device['name']}:", output)

        lldp_commands = []
        if enable_lldp:
            lldp_commands.append("lldp run")
        elif disable_lldp:
            lldp_commands.append("no lldp run")

        if lldp_commands:
            output = net_connect.send_config_set(lldp_commands)
            print(f"LLDP Configuration for {device['name']}:", output)

        net_connect.disconnect()
    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        print(f"Error connecting to {device['name']}: {e}")



def configure_spanning_tree(device, stp_mode, root_primary, root_vlan_id, root_secondary, root_secondary_vlan_id,
                            portfast_enable, portfast_disable, portfast_int_enable, portfast_int_disable):
    try:
        net_connect = ConnectHandler(**device["device_info"])
        net_connect.enable()

        if stp_mode == "pvst":
            output = net_connect.send_config_set(f"spanning-tree mode {stp_mode}")
            print(f"Spanning Tree Configuration for {device['name']}:", output)
        elif stp_mode == "rapid-pvst":
            output = net_connect.send_config_set(f"spanning-tree mode {stp_mode}")
            print(f"Spanning Tree Configuration for {device['name']}:", output)

        if root_primary and root_vlan_id:
            output = net_connect.send_config_set(f"spanning-tree vlan {root_vlan_id} root primary")
            print(f"Spanning Tree Configuration for {device['name']}:", output)
        
        if root_secondary and root_secondary_vlan_id:
            output = net_connect.send_config_set(f"spanning-tree vlan {root_secondary_vlan_id} root secondary")
            print(f"Spanning Tree Configuration for {device['name']}:", output)
        
        if portfast_enable and portfast_int_enable:
            ena_int = []
            ena_int.append(f"int range {portfast_int_enable}")
            ena_int.append("spanning-tree portfast")
            ena_int.append("spanning-tree bpduguard enable")
            output = net_connect.send_config_set(ena_int)
            print(f"Enabled PortFast for interfaces {portfast_int_enable} on device {device['name']}:", output)

        if portfast_int_disable and portfast_int_disable:
            dis_int = []
            dis_int.append(f"int range {portfast_int_disable}")
            dis_int.append("no spanning-tree portfast")
            output = net_connect.send_config_set(dis_int)
            print(f"Disable PortFast for interfaces {portfast_int_enable} on device {device['name']}:", output)

        net_connect.disconnect()
    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        print(f"Error configuring spanning tree on {device['name']}: {e}")
