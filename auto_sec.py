from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException

def automate_sec(device_info):
    try:
        device_info['timeout'] = 10  # กำหนด timeout
        net_connect = ConnectHandler(**device_info)
        net_connect.enable()

        config_commands = [
            'line con 0',
            'exec-timeout 3 0',
            'line vty 0 4',
            'exec-timeout 3 0',
            'no cdp run',
            'no lldp run',
            'no ip http server',
            'service password-encryption'
        ]
        output = net_connect.send_config_set(config_commands)
        print(f"Configuration applied to {device_info['ip']}: {output}")

        net_connect.disconnect()

        return True  

    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        print(f"Error connecting to {device_info['ip']}: {e}")
        return False  
