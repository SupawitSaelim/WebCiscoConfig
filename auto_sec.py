from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException

def automate_sec(device_info, db):
    try:
        device_info['timeout'] = 10  # กำหนด timeout
        net_connect = ConnectHandler(**device_info)
        net_connect.enable()

        device = db['devices'].find_one({"device_info.ip": device_info['ip']})
        print(device)

        if not device:
            print(f"Device with IP {device_info['ip']} not found in database.")
            return False

        warnings = device.get("analysis", {}).get("warnings", [])
        unused_ports = []
        for warning in warnings:
            if "Ports down" in warning:
                ports = warning.split(":")[-1].strip().split(", ")
                unused_ports.extend(ports)

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

        for port in unused_ports:
            config_commands.append(f"interface {port}")
            config_commands.append("shutdown")

        output = net_connect.send_config_set(config_commands)
        print(f"Configuration applied to {device_info['ip']}:\n{output}")

        net_connect.disconnect()
        return True  

    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        print(f"Error connecting to {device_info['ip']}: {e}")
        return False
