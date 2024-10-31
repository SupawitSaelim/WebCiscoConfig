import serial
import time

def send_command(ser, command):
    """Send a command to the device and return the output."""
    ser.write(command.encode() + b'\r\n')  #
    time.sleep(3)  
    return ser.read_all().decode('utf-8')  

def commands(consoleport, hostname, domainname, privilege_password, ssh_username, ssh_password, interface, ip_address,subnet_mask):
    """Initialize the device with the given parameters."""
    print(consoleport, hostname, domainname, privilege_password, ssh_username, ssh_password, interface, ip_address,subnet_mask)
    ser = serial.Serial(port=consoleport, baudrate=9600, timeout=3)
    
    # ส่งคำสั่งต่างๆ
    send_command(ser, 'enable')
    send_command(ser, 'conf t')
    send_command(ser, f'hostname {hostname}') 
    send_command(ser, f'ip domain-name {domainname}') 
    send_command(ser, f'enable password {privilege_password}') 
    send_command(ser, f'username {ssh_username} password {ssh_password}') 
    send_command(ser, f'int {interface}') 
    if ip_address == "dhcp":
        send_command(ser, 'ip address dhcp')  # Command to set IP to DHCP
    else:
        send_command(ser, f'ip address {ip_address} {subnet_mask}')
    send_command(ser, 'no sh')  

    # ปิดการเชื่อมต่อ
    ser.close()
