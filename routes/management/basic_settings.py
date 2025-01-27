from flask import Blueprint, render_template, request, redirect, url_for, flash
from pymongo.errors import ServerSelectionTimeoutError
import threading
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException
from core.device.device_config import configure_device

basic_settings = Blueprint('basic_settings', __name__)

def init_basic_settings(device_collection):
    @basic_settings.route('/basic_settings_page', methods=['GET'])
    def basic_settings_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
            flash("Database connection error. Please try again later.", "danger")
        return render_template('basic_settings.html', cisco_devices=cisco_devices)

    @basic_settings.route('/basic_settings', methods=['GET', 'POST'])
    def basic_settings_route():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
            flash("Database connection error. Please try again later.", "danger")
            return redirect(url_for('basic_settings.basic_settings_page'))

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
            configuration_results = []

            # Existing hostname check
            existing_device_hostname = device_collection.find_one({"name": hostname})
            if existing_device_hostname:
                flash("This hostname is already in use. Please choose a different hostname.", "danger")
                return redirect(url_for('basic_settings.basic_settings_page'))

            # Process multiple hostnames or single device
            try:
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
                                flash(f"Duplicate IP detected for device {name} with IP {ip_address}", "danger")
                                return redirect(url_for('basic_settings.basic_settings_page'))
                        
                        if not found_any:
                            flash(f"Device {name} not found in database", "danger")
                            return redirect(url_for('basic_settings.basic_settings_page'))
                        
                        device_names_processed.add(name)

                elif device_name:
                    device = device_collection.find_one({"device_info.ip": device_name})
                    if device:
                        device_ips.append(device["device_info"]["ip"])
                    else:
                        flash(f"Device with IP {device_name} not found in database", "danger")
                        return redirect(url_for('basic_settings.basic_settings_page'))

                # Configure devices and collect results
                threads = []
                results = []
                
                for ip in device_ips:
                    device = device_collection.find_one({"device_info.ip": ip})
                    if device:
                        # Update password if username matches and password changed
                        existing_username = device["device_info"].get("username")
                        if existing_username == username and password != device["device_info"].get("password"):
                            device_collection.update_one(
                                {"device_info.ip": ip},
                                {"$set": {"device_info.password": password}}
                            )

                        # Create thread for device configuration
                        result = {'ip': ip, 'status': None, 'error': None}
                        results.append(result)
                        
                        thread = threading.Thread(
                            target=configure_device_with_status,
                            args=(device, hostname, secret_password, banner,
                                  device_collection, enable_password_encryp,
                                  disable_password_encryp, username, password, result)
                        )
                        threads.append(thread)
                        thread.start()

                # Wait for all configurations to complete
                for thread in threads:
                    thread.join()

                # Process results and create appropriate flash messages
                success_devices = []
                failed_devices = []
                
                for result in results:
                    if result['status'] == 'success':
                        success_devices.append(result['ip'])
                    else:
                        failed_devices.append(f"{result['ip']}: {result['error']}")

                if success_devices:
                    flash(f"Configuration successful for devices: {', '.join(success_devices)}", "success")
                
                if failed_devices:
                    for device in failed_devices:
                        flash(f"Configuration failed for {device}", "danger")

            except Exception as e:
                flash(f"An unexpected error occurred: {str(e)}", "danger")

            return redirect(url_for('basic_settings.basic_settings_page'))

        return render_template('basic_settings.html', cisco_devices=cisco_devices)

    return basic_settings

def configure_device_with_status(device, hostname, secret_password, banner, 
                               device_collection, enable_password_encryp,
                               disable_password_encryp, username, password, result):
    """
    Wrapper function for configure_device that handles status updates
    """
    try:
        configure_device(device, hostname, secret_password, banner,
                        device_collection, enable_password_encryp,
                        disable_password_encryp, username, password)
        result['status'] = 'success'
    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        error_message = str(e)
        if "TCP connection to device failed" in error_message:
            error_message = ("TCP connection to device failed. Common causes: "
                           "1. Incorrect hostname or IP address. "
                           "2. Wrong TCP port. "
                           "3. Intermediate firewall blocking access.")
        result['status'] = 'failed'
        result['error'] = error_message
    except Exception as e:
        error_message = str(e)
        if "Pattern not detected:" in error_message: 
            error_message = "Unable to access privileged mode (#). Please ensure your enable password or secret password is correct."
        result['status'] = 'failed'
        result['error'] = error_message