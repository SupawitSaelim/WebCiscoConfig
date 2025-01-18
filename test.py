from netmiko import ConnectHandler

# ข้อมูลการเชื่อมต่อ
device = {
    'device_type': 'cisco_ios',
    'host': '192.168.0.3',
    'username': 'supawit',
    'password': 'admin',
    'secret': 'admin',  # รหัสผ่าน enable
}

# เชื่อมต่อไปยังอุปกรณ์
net_connect = ConnectHandler(**device)

# เข้าสู่โหมด enable
net_connect.enable()

# รีโหลดอุปกรณ์
reload_command = 'reload'
net_connect.send_command_timing(reload_command)

# สั่งให้รีโหลดโดยไม่ต้องยืนยัน
output = net_connect.send_command_timing('y')

print(output)

# สลับโหมด
switch_command = 'show version'  # ตัวอย่างการใช้คำสั่งในโหมด enable
output = net_connect.send_command(switch_command)
print(output)

# ปิดการเชื่อมต่อ
net_connect.disconnect()
