# เลือก Python image ที่เป็น official จาก Docker Hub
FROM python:3.13-slim

# ติดตั้ง Node.js และ npm
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    lsb-release \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_16.x | bash - \
    && apt-get install -y nodejs

# ตั้ง working directory ใน container
WORKDIR /app

# คัดลอกไฟล์ requirements.txt เข้าไปใน container
COPY requirements.txt .

# ติดตั้ง dependencies ที่ระบุใน requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกโค้ดทั้งหมดในโปรเจกต์เข้าไปใน container
COPY . .

# ติดตั้ง net-snmp ด้วย npm
RUN npm install net-snmp

# เปิด port ที่ Flask ใช้งาน (เช่น 5000)
EXPOSE 5000

# ตั้งค่าคำสั่งที่รันเมื่อ container ทำงาน
CMD ["python", "app.py"]
