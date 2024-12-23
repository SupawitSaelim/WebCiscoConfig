import re
import warnings
import joblib
import numpy as np
import string
import pandas as pd

# Disable specific sklearn warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

class NetworkConfigSecurityChecker:
    """
    A class to analyze network configuration security and password strength.
    """

    def __init__(self, model_path='lr_model.pkl'):
        """
        Initialize the security checker with a pre-trained model.
        
        Args:
            model_path (str): Path to the trained classification model
        """
        self.clf = joblib.load(model_path)

    def extract_features(self, password):
        """
        Extract features from a password.
        
        Args:
            password (str): Password to evaluate
        
        Returns:
            pd.DataFrame: Extracted features in the correct order
        """
        features = {
            'length': len(password),
            'digits': sum(c.isdigit() for c in password),
            'uppercase': sum(c.isupper() for c in password),
            'lowercase': sum(c.islower() for c in password),
            'special_chars': sum(c in string.punctuation for c in password),
        }
        feature_order = ['length', 'uppercase', 'lowercase', 'digits', 'special_chars']
        return pd.DataFrame([features])[feature_order]

    def predict_password_strength(self, password):
        """
        Predict the strength of a given password.
        
        Args:
            password (str): Password to evaluate
        
        Returns:
            str: Password strength category (Weak/Normal/Strong)
        """
        password_features = self.extract_features(password)
        result = self.clf.predict(password_features)[0]

        # Map prediction to strength categories
        strength_map = {0: "Weak", 1: "Normal", 2: "Strong"}
        return strength_map.get(result, "Unknown")

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
            if enable_password.startswith("7"):
                pass
            else:
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
        
        if "exec-timeout 0" in config:
            warnings.append("exec-timeout is set to 0, which is not recommended")
        
        if not re.search(r'line vty \d+ \d+\s+.*?exec-timeout\s+\d+\s+\d+', config, re.DOTALL):
            warnings.append("'exec-timeout' not set for line vty")
        
        if "no ip http server" not in config:
            warnings.append("Insecure HTTP server is enabled. Consider disabling it.")
        
        if "lldp run" in config:
            warnings.append("LLDP is enabled. Ensure it is necessary and properly secured.")
        
        if "no cdp run" not in config:
            warnings.append("CDP is enabled. Ensure it is necessary and secure.")
        
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
    enable password admin
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