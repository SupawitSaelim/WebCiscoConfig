import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")


# โหลดโมเดลจากไฟล์
clf = joblib.load('model.pkl')
print("Model loaded successfully.")

# โหลด vectorizer ที่ถูกบันทึกไว้
vectorizer = joblib.load('vectorizer.pkl')
print("Vectorizer loaded successfully.")

def main():
    password = input("Enter a password : ")
    sample_array = np.array([password])
    sample_matrix = vectorizer.transform(sample_array)
    
    length_pass = len(password)
    length_normalised_lowercase = len([char for char in password if char.islower()]) / len(password)
    
    # รวมข้อมูลที่ได้เป็น feature ใหม่
    new_matrix2 = np.append(sample_matrix.toarray(), (length_pass, length_normalised_lowercase)).reshape(1, 101)
    result = clf.predict(new_matrix2)
    
    if result == 0:
        return "Password is weak"
    elif result == 1:
        return "Password is normal"
    else:
        return "Password is strong"

if __name__ == "__main__":
    while(True):
        print(main())
