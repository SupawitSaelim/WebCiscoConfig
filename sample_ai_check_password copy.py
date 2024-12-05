import re
from sklearn.ensemble import RandomForestClassifier

# ตัวอย่าง config จาก show running-config
config = """
version 15.2
hostname Switch
service password-encryption
!
!
enable password 7 05080F1C2243
!
line con 0
 password supawit
 logging synchronous
 exec-timeout 3 0
line aux 0
!
line vty 0 4
 login local
 transport input ssh
line vty 5 15
 login
!
end
"""

# ตัวอย่าง output จาก show ip interface brief
ip_interface_brief = """
Interface              IP-Address      OK? Method Status                Protocol
Vlan1                  192.168.0.9     YES manual up                    up
FastEthernet0/1        unassigned      YES unset  up                    down
FastEthernet0/2        unassigned      YES unset  administratively down down
FastEthernet0/3        unassigned      YES unset  up                    down
FastEthernet0/4        unassigned      YES unset  up                    down
FastEthernet0/5        unassigned      YES unset  up                    down
"""

# ตรวจสอบ password
passwords = re.findall(r'password\s+(\S+)', config)

insecure_passwords = ['cisco', 'enable', 'switch', 'router', 'admin']

insecure_password_flag = 0
for password in passwords:
    if password in insecure_passwords:
        insecure_password_flag = 1
        print(f"Warning: Insecure password '{password}' found! Please change it.")

# ตรวจสอบการเข้ารหัส password
if "no service password-encryption" in config:
    password_encryption_flag = 1  
    print("Warning: Password encryption is not enabled. Please enable 'service password-encryption'.")
else:
    password_encryption_flag = 0  

# ตรวจสอบสถานะของพอร์ตจาก show ip interface brief
down_ports = re.findall(r'^\s*(\S+)\s+\S+\s+\S+\s+\S+\s+(down)', ip_interface_brief, re.MULTILINE)
down_ports_flag = 1 if down_ports else 0  # 1 ถ้ามีพอร์ต down, 0 ถ้าไม่มี

if down_ports:
    down_ports_list = [port[0] for port in down_ports]  # ดึงชื่อพอร์ตที่อยู่ในสถานะ down
    print(f"Warning: The following ports are down: {', '.join(down_ports_list)}. Please consider shutting them down for security.")

# ตรวจสอบการตั้งค่า exec-timeout ใน line vty และ line con
exec_timeout_flag = 0  # 0 = safe, 1 = unsafe
if not re.search(r'line con 0\s+.*?exec-timeout\s+\d+\s+\d+', config, re.DOTALL):
    exec_timeout_flag = 1
    print("Warning: 'exec-timeout' not set for line con. Please consider adding 'exec-timeout 3'.")
if not re.search(r'line vty \d+ \d+\s+.*?exec-timeout\s+\d+\s+\d+', config, re.DOTALL):
    exec_timeout_flag = 1
    print("Warning: 'exec-timeout' not set for line vty. Please consider adding 'exec-timeout 3'.")

# ตรวจสอบการตั้งค่า SSH ใน line vty
vty_config = re.findall(r'line vty \d+ \d+\s+.*?transport input (\S+)', config, re.DOTALL)

ssh_flag = 1  # 1 ถ้าใช้ ssh, 0 ถ้าใช้ telnet หรือ all
if vty_config:
    for transport in vty_config:
        if transport == 'ssh':
            ssh_flag = 1
            break
        elif transport == 'telnet' or transport == 'all':
            ssh_flag = 0
            print("Warning: Telnet or 'all' is configured for vty lines. Please consider using SSH for security.")

# ฟีเจอร์การฝึก AI (ตัวอย่าง)
# ปรับ X ให้รวม exec_timeout_flag
X = [
    [1, 1, 1, 0, 1],  # unsafe config (password และไม่มี password-encryption, ports down, no ssh, exec-timeout not set)
    [0, 0, 0, 1, 0],  # safe config (password และมี password-encryption, no ports down, ssh, exec-timeout set)
    [1, 0, 1, 0, 1],  # unsafe config (password ที่ไม่ปลอดภัย แต่มี password-encryption, ports down, no ssh, exec-timeout not set)
    [0, 1, 0, 1, 0]   # unsafe config (password ปลอดภัย แต่ไม่มี password-encryption, no ports down, ssh, exec-timeout set)
]
y = [1, 0, 1, 1]  # labels: 1 = unsafe, 0 = safe

# สร้างโมเดล Random Forest
model = RandomForestClassifier()
model.fit(X, y)

# สร้างฟีเจอร์ใหม่จาก config ที่เราตรวจสอบ
new_config = [insecure_password_flag, password_encryption_flag, down_ports_flag, ssh_flag, exec_timeout_flag]  # config ที่ดึงจาก config จริง

prediction = model.predict([new_config])
if prediction == 1:
    print("This configuration is flagged as unsafe.")
else:
    print("This configuration is safe.")
