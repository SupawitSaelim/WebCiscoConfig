import serial
import time

def send_command(ser, command):
    ser.write(command.encode() + b'\r\n')  #
    time.sleep(3)
    output = ser.read_all().decode('utf-8')  # อ่านผลลัพธ์ที่ได้
    print(f"Received output: {output}")
    return ser.read_all().decode('utf-8')  

def convert_cidr_to_netmask(cidr):
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

def commands(consoleport, hostname, domainname, privilege_password, ssh_username, ssh_password, interface, ip_address):
    print(consoleport, hostname, domainname, privilege_password, ssh_username, ssh_password, interface, ip_address)
    ser = serial.Serial(port=consoleport, baudrate=9600, timeout=3)
    
    # แยก IP และ CIDR
    if '/' in ip_address:
        ip, cidr = ip_address.split('/')
        subnet_mask = convert_cidr_to_netmask(ip_address)  # แปลง CIDR เป็น subnet mask
        print(subnet_mask)
    else:
        ip = ip_address
        subnet_mask = "255.255.255.0"  # กำหนดค่า subnet mask เป็นค่า default หากไม่มี CIDR

    # ส่งคำสั่งต่างๆ
    send_command(ser, 'enable')
    send_command(ser, 'conf t')
    send_command(ser, f'hostname {hostname}') 
    send_command(ser, f'ip domain-name {domainname}') 
    send_command(ser, f'enable se {privilege_password}') 
    send_command(ser, f'username {ssh_username} password {ssh_password}') 
    send_command(ser, f'int {interface}') 
    if ip_address == "dhcp":
        send_command(ser, 'ip address dhcp')  # Command to set IP to DHCP
    else:
        send_command(ser, f'ip address {ip} {subnet_mask}')
    send_command(ser, 'no sh')  
    send_command(ser, 'line vty 0 4')
    send_command(ser, 'transport input ssh') 
    send_command(ser, 'login local')
    send_command(ser, 'crypto key generate rsa general-keys modulus 1024')
    send_command(ser, 'end')
    send_command(ser, 'wri')

    # ปิดการเชื่อมต่อ
    ser.close()
