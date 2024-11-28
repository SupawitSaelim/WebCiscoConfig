import serial
import time

def send_command(ser, command):
    # Send the command to the terminal
    ser.write(command.encode() + b'\r\n')  # Ensure the command is followed by a newline and carriage return
    time.sleep(3)  # Allow the terminal time to process the command

    # Read the output
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
    
    # Open serial port connection
    ser = serial.Serial(port=consoleport, baudrate=9600, timeout=3)
    
    # Split IP and CIDR if necessary
    if '/' in ip_address:
        ip, cidr = ip_address.split('/')
        subnet_mask = convert_cidr_to_netmask(ip_address)
        print(subnet_mask)
    else:
        ip = ip_address
        subnet_mask = "255.255.255.0"

    # Send an empty command to capture the initial output (like configuration prompts)
    output = send_command(ser, '')
    print("1", output)  # Debugging: Check what we get after sending the command

    # Check for the initial configuration dialog prompt
    if "Would you like to enter the initial configuration dialog? [yes/no]:" in output:
        print("Detected terminal asking for initial configuration, sending 'no' and waiting.")
        send_command(ser, 'no')  # Send 'no' to skip initial configuration dialog
        
        # Wait until we enter the `>` prompt (indicating we're in user exec mode)
        while '>' not in output:
            send_command(ser, '\n')  # Send a newline (Enter) to continue the terminal's prompt
            output = send_command(ser, '')  # Read the output after sending newline
            print(f"Waiting for prompt: {output}")  # Debugging: Check the output

        print("Entered user exec mode, proceeding to enable mode.")
    else:
        print("Initial configuration prompt not detected, continuing...")

    # Continue with the configuration commands
    send_command(ser, 'enable')  # Enter enable mode
    send_command(ser, 'conf t')  # Enter global configuration mode
    send_command(ser, f'hostname {hostname}')  # Set the hostname
    send_command(ser, f'ip domain-name {domainname}')  # Set the domain name
    send_command(ser, f'enable secret {privilege_password}')  # Set privilege password
    send_command(ser, f'username {ssh_username} password {ssh_password}')  # Set SSH username and password
    send_command(ser, f'int {interface}')  # Configure interface
    if ip_address == "dhcp":
        send_command(ser, 'ip address dhcp')  # Set IP to DHCP
    else:
        send_command(ser, f'ip address {ip} {subnet_mask}')  # Set static IP and subnet mask
    send_command(ser, 'no shutdown')  # Enable interface (no shutdown)
    send_command(ser, 'line vty 0 4')  # Configure VTY lines for SSH access
    send_command(ser, 'transport input ssh')  # Allow SSH input on VTY lines
    send_command(ser, 'login local')  # Enable local login
    send_command(ser, 'crypto key generate rsa general-keys modulus 1024')  # Generate RSA keys
    send_command(ser, 'end')  # Exit configuration mode
    if save_startup:
        send_command(ser, 'write memory')  # Save the configuration

    # Close serial connection
    ser.close()

