from datetime import datetime
from netmiko import ConnectHandler
import pytz
from ai_password_with_re import NetworkConfigSecurityChecker

class SecurityChecker:
    def __init__(self, device_collection, model_path, timezone):
        self.device_collection = device_collection
        self.model_path = model_path
        self.timezone = pytz.timezone(timezone)
        self.security_checker = self.load_model()

    def load_model(self):
        return NetworkConfigSecurityChecker(model_path=self.model_path)

    def fetch_and_analyze(self):
        devices = list(self.device_collection.find())
        for device in devices:
            device_info = device["device_info"]
            try:
                net_connect = ConnectHandler(**device_info)
                net_connect.enable()

                show_run = net_connect.send_command("show running-config")
                show_ip_int_br = net_connect.send_command("show ip interface brief")
                net_connect.disconnect()

                warnings = self.security_checker.analyze_config_security(show_run, show_ip_int_br)
                current_time = datetime.now(self.timezone)
                formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

                self.device_collection.update_one(
                    {"_id": device["_id"]},
                    {"$set": {"analysis": {"warnings": warnings, "last_updated": formatted_time}}}
                )
            except Exception as e:
                print(f"Error processing {device['device_info']['ip']}: {e}")
