import re
import warnings

import joblib
import numpy as np

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

clf = joblib.load('model.pkl')
vectorizer = joblib.load('vectorizer.pkl')

config = """
version 15.2
hostname Switch
service password-encryption
!
!
enable password Supawitadmin123_
!
line con 0
 password Supawitadmin123_
 logging synchronous
 exec-timeout 3 0
line aux 0
!
!
end
"""

def predict_password_strength(password):
    sample_array = np.array([password])
    sample_matrix = vectorizer.transform(sample_array)

    length_pass = len(password)
    length_normalised_lowercase = len([char for char in password if char.islower()]) / len(password)

    new_matrix2 = np.append(sample_matrix.toarray(), (length_pass, length_normalised_lowercase)).reshape(1, 101)
    result = clf.predict(new_matrix2)

    if result == 0:
        return "Weak"
    elif result == 1:
        return "Normal"
    else:
        return "Strong"

def check_passwords_in_config(config):
    passwords = re.findall(r'password\s+(\S+)', config)

    for password in passwords:
        strength = predict_password_strength(password)
        if strength == "Weak" or strength == "Normal":
            print(f"Warning: Insecure password '{password}' found! Strength: {strength}. Please change it.")

if __name__ == "__main__":
    check_passwords_in_config(config)
