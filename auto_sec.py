from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException

def automate_sec(device_info, db):
    try:
        # Set default timeout
        device_info['timeout'] = 10
        
        # Ensure all required fields are present
        required_fields = ['device_type', 'ip', 'username', 'password']
        if not all(field in device_info for field in required_fields):
            print(f"Missing required device information: {[f for f in required_fields if f not in device_info]}")
            return False

        # Connect to device
        net_connect = ConnectHandler(**device_info)
        
        # Enter enable mode if secret is provided
        if 'secret' in device_info and device_info['secret']:
            net_connect.enable()

        # Find device in database
        device = db.devices.find_one({"device_info.ip": device_info['ip']})
        if not device:
            print(f"Device with IP {device_info['ip']} not found in database.")
            return False

        # Get warnings
        warnings = device.get("analysis", {}).get("warnings", [])
        unused_ports = []
        
        # Extract unused ports from warnings
        for warning in warnings:
            if "Ports down" in warning:
                ports = warning.split(":")[-1].strip().split(", ")
                unused_ports.extend(ports)

        # Prepare configuration commands
        config_commands = [
            'line con 0',
            'exec-timeout 3 0',
            'line vty 0 4',
            'transport input ssh',  # Fixed typo in 'transport'
            'exec-timeout 3 0',
            'no cdp run',
            'no lldp run',
            'no ip http server',
            'service password-encryption'
        ]

        # Add shutdown commands for unused ports
        for port in unused_ports:
            config_commands.extend([
                f"interface {port}",
                "shutdown"
            ])

        # Send configuration
        try:
            output = net_connect.send_config_set(config_commands)
            print(f"Configuration applied to {device_info['ip']}:\n{output}")
            net_connect.save_config()  # Save the configuration
            return True
        except Exception as e:
            print(f"Error applying configuration: {str(e)}")
            return False
        finally:
            net_connect.disconnect()

    except NetMikoTimeoutException as e:
        print(f"Timeout connecting to {device_info['ip']}: {str(e)}")
        return False
    except NetMikoAuthenticationException as e:
        print(f"Authentication failed for {device_info['ip']}: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return False