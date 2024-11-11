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
