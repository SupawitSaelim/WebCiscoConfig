from flask import Blueprint, render_template, request, redirect, url_for, flash
from pymongo.errors import ServerSelectionTimeoutError
import threading
from device_config import configure_device

basic_settings = Blueprint('basic_settings', __name__)

def init_basic_settings(device_collection):
    @basic_settings.route('/basic_settings_page', methods=['GET'])
    def basic_settings_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
        
        return render_template('basic_settings.html', cisco_devices=cisco_devices)

    @basic_settings.route('/basic_settings', methods=['GET', 'POST'])
    def basic_settings_route():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None

        if request.method == 'POST':
            device_name = request.form.get('device_name')
            hostname = request.form.get('hostname')
            secret_password = request.form.get('secret_password')
            banner = request.form.get('banner')
            many_hostname = request.form.get('many_hostname')
            enable_password_encryp = request.form.get('enable_password_encryp')
            disable_password_encryp = request.form.get('disable_password_encryp')
            username = request.form.get('username')
            password = request.form.get('password')
            
            device_ips = []
            device_names_processed = set()

            # Check for existing hostname
            existing_device_hostname = device_collection.find_one({"name": hostname})
            if existing_device_hostname:
                flash("This hostname is already in use. Please choose a different hostname.", "danger")
                return redirect(url_for('basic_settings.basic_settings_page'))

            # Process multiple hostnames
            if many_hostname:
                device_names = [name.strip() for name in many_hostname.split(',')]
                for name in device_names:
                    if name in device_names_processed:
                        continue
                    
                    devices = device_collection.find({"name": name})
                    found_any = False
                    
                    for device in devices:
                        ip_address = device["device_info"]["ip"]
                        if ip_address not in device_ips:
                            device_ips.append(ip_address)
                            found_any = True
                        else:
                            return f'<script>alert("Duplicate IP detected for device {name} with IP {ip_address}"); window.location.href="/basic_settings";</script>'
                    
                    if not found_any:
                        return f'<script>alert("Device {name} not found in database"); window.location.href="/basic_settings";</script>'
                    
                    device_names_processed.add(name)

            # Process single device
            elif device_name:
                device = device_collection.find_one({"device_info.ip": device_name})
                if device:
                    device_ips.append(device["device_info"]["ip"])
                else:
                    return f'<script>alert("Device with IP {device_name} not found in database"); window.location.href="/basic_settings";</script>'

            threads = []
            print("Device IPs to configure:", device_ips)
            
            # Configure devices
            for ip in device_ips:
                device = device_collection.find_one({"device_info.ip": ip})
                
                if device:
                    existing_username = device["device_info"].get("username")
                    if existing_username == username:
                        if password != device["device_info"].get("password"):
                            device_collection.update_one(
                                {"device_info.ip": ip},
                                {"$set": {"device_info.password": password}}
                            )
                            print(f"Password for {username} updated on device {ip}")

                    thread = threading.Thread(
                        target=configure_device,
                        args=(device, hostname, secret_password, banner,
                              device_collection, enable_password_encryp,
                              disable_password_encryp, username, password)
                    )
                    threads.append(thread)
                    thread.start()
                else:
                    return f'<script>alert("Device with IP {ip} not found in database"); window.location.href="/basic_settings";</script>'

            for thread in threads:
                thread.join()

            flash("Configuration successful for devices: " + ", ".join(device_ips), "success")
            return redirect(url_for('basic_settings.basic_settings_page'))

        return render_template('basic_settings.html', cisco_devices=cisco_devices)

    return basic_settings