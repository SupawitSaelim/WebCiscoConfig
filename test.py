import random
import string

# ฟังก์ชันสำหรับสร้างรหัสผ่านแบบสุ่ม
def generate_password(length=8):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

# ฟังก์ชันสำหรับกำหนดระดับความแข็งแรงของรหัสผ่าน
def password_strength(password):
    if len(password) < 6:
        return 0  # อ่อน
    elif len(password) < 10:
        return 1  # ปานกลาง
    else:
        return 2  # แข็งแรง

# สร้างข้อมูลรหัสผ่านและระดับความแข็งแรง
password_data = []
for _ in range(10):
    pwd = generate_password(random.randint(6, 12))
    strength = password_strength(pwd)
    password_data.append((pwd, strength))

# สร้างไฟล์ SQL
with open("passwords.sql", "w") as f:
    f.write("CREATE TABLE passwords (password TEXT, strength INTEGER);\n")
    f.write("INSERT INTO passwords (password, strength) VALUES\n")
    values = [f"('{pwd}', {strength})" for pwd, strength in password_data]
    f.write(",\n".join(values) + ";\n")

print("ไฟล์ passwords.sql ถูกสร้างเรียบร้อยแล้ว!")