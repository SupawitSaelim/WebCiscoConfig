import serial
import time
from serial.tools import list_ports

def get_available_ports():
    ports = list_ports.comports()
    return [{"port": port.device, "description": port.description} for port in ports]

def validate_port(consoleport):
    """Validate if the selected port exists"""
    available_ports = get_available_ports()
    available_port_names = [p["port"] for p in available_ports]
    
    if consoleport not in available_port_names:
        return {
            "valid": False,
            "error": "Invalid COM port selected",
            "message": f"The selected port '{consoleport}' is not available.",
            "available_ports": available_ports
        }
    return {"valid": True}

def get_available_interfaces(ser):
    """Get list of available interfaces from the device"""
    send_command(ser, 'enable')
    output = send_command(ser, 'show ip int br')
    output = output.replace('&lt;br&gt;', '\n').replace('&#39;', "'")
    return output

def send_command(ser, command):
    ser.write(command.encode() + b'\r\n')  # Ensure the command is followed by a newline and carriage return
    time.sleep(3)  # Allow the terminal time to process the command

    output = ''
    while ser.in_waiting > 0:
        output += ser.read(ser.in_waiting).decode('utf-8')  # Read all available data in the buffer
        time.sleep(0.5)  # Allow time for additional output

    print(f"Received output: {output}")  # Debugging: print full output
    
    return output

def convert_cidr_to_netmask(cidr):
    if '/' in cidr:
        ip, bits = cidr.split('/')  # Split IP and CIDR
        bits = int(bits)
    else:
        bits = int(cidr)

    netmask = []
    for i in range(4):
        if bits >= 8:
            netmask.append(255)
            bits -= 8
        else:
            netmask.append(256 - 2**(8 - bits))  # Calculate subnet mask
            bits = 0
    return '.'.join(map(str, netmask))

def commands(consoleport, hostname, domainname, privilege_password, ssh_username, ssh_password, interface, ip_address, save_startup):
    print(consoleport, hostname, domainname, privilege_password, ssh_username, ssh_password, interface, ip_address, save_startup)
    port_check = validate_port(consoleport)
    if not port_check["valid"]:
        return port_check

    try:
        ser = serial.Serial(port=consoleport, baudrate=9600, timeout=3)
    except serial.SerialException as e:
        return {
            "valid": False,
            "error": "COM Port Error",
            "message": f"Could not open port {consoleport}: {str(e)}",
            "available_ports": get_available_ports()
        }

    try:
        if '/' in ip_address:
            ip, cidr = ip_address.split('/')
            subnet_mask = convert_cidr_to_netmask(ip_address)
        else:
            ip = ip_address
            subnet_mask = "255.255.255.0"

        # Initial dialog check and configuration - keeping this exactly as is
        output = send_command(ser, '')
        
        if "Would you like to enter the initial configuration dialog? [yes/no]:" in output:
            print("Detected terminal asking for initial configuration, sending 'no' and waiting.")
            send_command(ser, 'no')
            
            while '>' not in output:
                send_command(ser, '\n')
                output = send_command(ser, '')
                print(f"Waiting for prompt: {output}")

            print("Entered user exec mode, proceeding to enable mode.")
        else:
            print("Initial configuration prompt not detected, continuing...")

        interfaces_output = get_available_interfaces(ser)

        # Rest of the configuration commands - keeping these exactly as is
        send_command(ser, 'enable')
        send_command(ser, 'conf t')
        output = send_command(ser, f'int {interface}')
        output = output.strip() 
        output = output.replace("\r\n", " ").replace("\n", " ")
        
        if "Invalid input detected" in output or "^" in output:
            send_command(ser, 'end')
            ser.close()
            return {
                "error": "Invalid Interface",
                "message": f"The interface '{interface}' is not valid or doesn't exist on this device.",
                "available_interfaces": interfaces_output
            }

        send_command(ser, f'int {interface}')
        send_command(ser, f'no switchport')
        if ip_address == "dhcp":
            send_command(ser, 'ip address dhcp')
        else:
            send_command(ser, f'ip address {ip} {subnet_mask}')
        send_command(ser, 'no shutdown')

        send_command(ser, 'conf t')
        send_command(ser, f'hostname {hostname}')
        send_command(ser, f'ip domain-name {domainname}')
        send_command(ser, f'enable password {privilege_password}')
        send_command(ser, f'username {ssh_username} password {ssh_password}')
        send_command(ser, 'line vty 0 4')
        send_command(ser, 'transport input all')
        send_command(ser, 'login local')
        send_command(ser, 'crypto key generate rsa general-keys modulus 1024')
        send_command(ser, 'end')
        
        if save_startup:
            send_command(ser, 'write memory')

        ser.close()
        return None  # Success case

    except Exception as e:
        if ser and ser.is_open:
            ser.close()
        return {
            "valid": False,
            "error": "Configuration Error",
            "message": str(e).replace('&#39;', "'"),
            "available_ports": get_available_ports()
        }

