import joblib
import pandas as pd
import warnings
import string
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

# โหลดโมเดล
model = joblib.load('dt_model.pkl')

# ลำดับฟีเจอร์ที่โมเดลคาดหวัง
feature_order = ['length', 'uppercase', 'lowercase', 'digits', 'special_chars']

def extract_features(password):
    """แปลงรหัสผ่านให้เป็นฟีเจอร์ในลำดับที่ถูกต้อง"""
    features = {
        'length': len(password),
        'digits': sum(c.isdigit() for c in password),
        'uppercase': sum(c.isupper() for c in password),
        'lowercase': sum(c.islower() for c in password),
        'special_chars': sum(c in string.punctuation for c in password),
    }
    return pd.DataFrame([features])[feature_order]  # เรียงลำดับฟีเจอร์ให้ตรง

def main():
    password = input("Enter a password: ")
    # แปลงรหัสผ่านเป็นฟีเจอร์
    password_features = extract_features(password)
    result = model.predict(password_features)[0]
    
    if result == 0:
        return "Password is weak"
    elif result == 1:
        return "Password is normal"
    else:
        return "Password is strong"

if __name__ == "__main__":
    while True:
        print(main())
