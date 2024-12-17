import os
from dotenv import load_dotenv

# โหลดค่าจากไฟล์ .env
load_dotenv()

print(f"MONGO_URI: {os.getenv('MONGO_URI')}")
