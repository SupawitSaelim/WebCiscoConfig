import re
import warnings
import joblib
import numpy as np

# Disable specific sklearn warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

class NetworkConfigSecurityChecker:
    """
    A class to analyze network configuration security and password strength.
    
    This class provides methods to:
    - Check password strength
    - Analyze configuration security
    - Identify potential security risks in network configurations
    """

    def __init__(self, model_path='model.pkl', vectorizer_path='vectorizer.pkl'):
        """
        Initialize the security checker with pre-trained model and vectorizer.
        
        Args:
            model_path (str): Path to the trained classification model
            vectorizer_path (str): Path to the text vectorizer
        """
        self.clf = joblib.load(model_path)
        self.vectorizer = joblib.load(vectorizer_path)

    def predict_password_strength(self, password):
        """
        Predict the strength of a given password.
        
        Args:
            password (str): Password to evaluate
        
        Returns:
            str: Password strength category (Weak/Normal/Strong)
        """
        # Prepare password for prediction
        sample_array = np.array([password])
        sample_matrix = self.vectorizer.transform(sample_array)

        # Calculate additional features
        length_pass = len(password)
        length_normalised_lowercase = len([char for char in password if char.islower()]) / len(password)

        # Combine features for prediction
        new_matrix = np.append(sample_matrix.toarray(), (length_pass, length_normalised_lowercase)).reshape(1, 101)
        result = self.clf.predict(new_matrix)

        # Map prediction to strength categories
        strength_map = {0: "Weak", 1: "Normal", 2: "Strong"}
        return strength_map.get(result[0], "Unknown")

    def analyze_config_security(self, config, ip_interface_brief):
        """
        Analyze network configuration for potential security issues.
        
        Args:
            config (str): Network device configuration
            ip_interface_brief (str): Output of 'show ip interface brief'
        
        Returns:
            list: Warnings and security recommendations
        """
        warnings = []

        enable_password_match = re.search(r'enable password\s+(\S+)', config)
        if enable_password_match:
            enable_password = enable_password_match.group(1)
            strength = self.predict_password_strength(enable_password)
            if strength in ["Weak", "Normal"]:
                warnings.append(f"Insecure enable password found! Strength: {strength}")

        username_password_matches = re.findall(r'username\s+(\S+)\s+password\s+\S+\s+(\S+)', config)
        for username, password in username_password_matches:
            strength = self.predict_password_strength(password)
            if strength in ["Weak", "Normal"]:
                warnings.append(f"Insecure password for username '{username}' found! Strength: {strength}")


        if "no service password-encryption" in config:
            warnings.append("Password encryption is not enabled")

        # Check interface status
        down_ports = re.findall(r'^\s*(\S+)\s+\S+\s+\S+\s+\S+\s+(down)', ip_interface_brief, re.MULTILINE)
        if down_ports:
            down_ports_list = [port[0] for port in down_ports]
            warnings.append(f"Ports down (should consider administratively shutting them down if unused): {', '.join(down_ports_list)}")

        # Check exec-timeout configurations
        if not re.search(r'line con 0\s+.*?exec-timeout\s+\d+\s+\d+', config, re.DOTALL):
            warnings.append("'exec-timeout' not set for line con")
        
        if not re.search(r'line vty \d+ \d+\s+.*?exec-timeout\s+\d+\s+\d+', config, re.DOTALL):
            warnings.append("'exec-timeout' not set for line vty")
        
        # Check VTY transport settings
        vty_config = re.findall(r'line vty \d+ \d+\s+.*?transport input (\S+)', config, re.DOTALL)
        for transport in vty_config:
            if transport in ['telnet', 'all']:
                warnings.append(f"Insecure transport method '{transport}' configured for VTY")

        return warnings

def main():
    """
    Main function to demonstrate the usage of NetworkConfigSecurityChecker.
    """
    # Example configuration and interface brief
    config = """
    version 15.2
    hostname Switch
    no service password-encryption
    !
    enable password Supawitadmin123_
    !
    line con 0
     password Supawitadmin123_
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

    ip_interface_brief = """
    Interface              IP-Address      OK? Method Status                Protocol
    Vlan1                  192.168.0.9     YES manual up                    up
    FastEthernet0/1        unassigned      YES unset  up                    down
    FastEthernet0/2        unassigned      YES unset  administratively down down
    FastEthernet0/3        unassigned      YES unset  up                    down
    FastEthernet0/4        unassigned      YES unset  up                    down
    FastEthernet0/5        unassigned      YES unset  up                    down
    """

    # Initialize security checker
    security_checker = NetworkConfigSecurityChecker()

    # Analyze configuration
    config_warnings = security_checker.analyze_config_security(config, ip_interface_brief)

    # Print warnings
    if config_warnings:
        print("Security Warnings:")
        for warning in config_warnings:
            print(f"- {warning}")
    else:
        print("No security issues detected.")

if __name__ == "__main__":
    main()