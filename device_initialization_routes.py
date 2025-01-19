from flask import Blueprint, render_template, request, flash
from datetime import datetime
import pytz
import serial_script

device_init_bp = Blueprint('device_initialization', __name__)

def init_device_initialization_routes(device_collection):
    @device_init_bp.route('/initialization_page', methods=['GET'])
    def initialization_page():
        return render_template('initialization.html')

    @device_init_bp.route('/initialization', methods=['GET', 'POST'])
    def initialization():
        if request.method == 'POST':
            consoleport = request.form.get('consoleport')
            hostname = request.form.get('hostname')
            domainname = request.form.get('domainname')
            privilege_password = request.form.get('privilegepassword')
            ssh_username = request.form.get('ssh_username')
            ssh_password = request.form.get('ssh_password')
            interface = request.form.get('interface')
            interface_type = request.form.get('interfaceType')
            ip_address = request.form.get('ip_address')
            save_startup = True
            tz_bangkok = pytz.timezone('Asia/Bangkok')
            current_time = datetime.now(tz_bangkok).replace(microsecond=0)

            if interface_type == "DHCP":
                ip_address = "dhcp"
            else:
                if not ip_address:
                    flash("Please provide an IP address for Manual configuration.", 'danger')
                    return render_template('initialization.html')

            try:
                if ip_address != "dhcp":
                    if "/" in ip_address:
                        ip_address_split = ip_address.split('/')[0]

                    device_data = {
                        "name": hostname,
                        "device_info": {
                            "device_type": "cisco_ios",
                            "ip": ip_address_split,
                            "username": ssh_username,
                            "password": ssh_password,
                            "secret": privilege_password,
                            "session_log": "output.log"
                        },
                        "timestamp": current_time
                    }

                    # ตรวจสอบ hostname และ IP ซ้ำ
                    existing_device_hostname = device_collection.find_one({"name": hostname})
                    if existing_device_hostname:
                        flash("This hostname is already in use. Please choose a different hostname.", "danger")
                        return render_template('initialization.html', hostname_duplicate="This hostname is already in use. Please enter a different hostname.")

                    existing_device = device_collection.find_one({"device_info.ip": ip_address_split})
                    if existing_device:
                        return render_template('initialization.html', ip_duplicate="This IP address is already in use. Please enter a different IP address.")
                    
                    output = serial_script.commands(consoleport, hostname, domainname, privilege_password,
                                       ssh_username, ssh_password, interface, ip_address, save_startup)
                    if output is not None and "Invalid interface input" in output:
                        flash("Invalid interface input. Please provide a valid interface.", "danger")
                        return render_template('initialization.html', error="Invalid interface input. Please try again.")

                    device_collection.insert_one(device_data)
                else:
                    output = serial_script.commands(consoleport, hostname, domainname, privilege_password,
                                       ssh_username, ssh_password, interface, ip_address, save_startup)
                    if output is not None and "Invalid interface input" in output:
                        flash("Invalid interface input. Please provide a valid interface.", "danger")
                        return render_template('initialization.html', error="Invalid interface input. Please try again.")

                return render_template('initialization.html', success="Device successfully initialized!")

            except Exception as e:
                return render_template('initialization.html', error=f"An error occurred: {e}")

        return render_template('initialization.html')

    return device_init_bp
