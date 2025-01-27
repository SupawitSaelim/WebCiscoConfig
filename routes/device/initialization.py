from flask import Blueprint, render_template, request, flash, jsonify
from datetime import datetime
import pytz
import utils.serial_script as serial_script
from serial.tools import list_ports
import html

device_init_bp = Blueprint('device_initialization', __name__)

def get_available_ports():
    ports = list_ports.comports()
    return [{"port": port.device, "description": port.description} for port in ports]

def init_device_initialization_routes(device_collection):
    @device_init_bp.route('/get_ports', methods=['GET'])
    def get_ports():
        available_ports = get_available_ports()
        return jsonify(available_ports)

    @device_init_bp.route('/initialization_page', methods=['GET']) 
    def initialization_page():
        available_ports = get_available_ports()
        return render_template('initialization.html', available_ports=available_ports)

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

            if not consoleport:
                flash("Please select a COM port", 'danger')
                return render_template('initialization.html', available_ports=get_available_ports())

            if interface_type == "DHCP":
                ip_address = "dhcp"
            else:
                if not ip_address:
                    flash("Please provide an IP address for Manual configuration.", 'danger')
                    return render_template('initialization.html', available_ports=get_available_ports())

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

                    existing_device_hostname = device_collection.find_one({"name": hostname})
                    if existing_device_hostname:
                        flash("This hostname is already in use. Please choose a different hostname.", "danger")
                        return render_template('initialization.html', hostname_duplicate="This hostname is already in use. Please enter a different hostname.", available_ports=get_available_ports())

                    existing_device = device_collection.find_one({"device_info.ip": ip_address_split})
                    if existing_device:
                        return render_template('initialization.html', ip_duplicate="This IP address is already in use. Please enter a different IP address.", available_ports=get_available_ports())
                    
                    output = serial_script.commands(consoleport, hostname, domainname, privilege_password,
                                       ssh_username, ssh_password, interface, ip_address, save_startup)
                    
                    if isinstance(output, dict) and "error" in output:
                        error_msg = f"{output['error']}: {output['message']}"
                        if "available_interfaces" in output:
                            interfaces_output = html.unescape(output['available_interfaces'])
                            error_msg += f"\n\nAvailable interfaces:\n{interfaces_output}"
                        flash(error_msg, 'danger')
                        return render_template('initialization.html', error=error_msg, 
                                            available_ports=get_available_ports())

                    device_collection.insert_one(device_data)
                else:
                    output = serial_script.commands(consoleport, hostname, domainname, privilege_password,
                                       ssh_username, ssh_password, interface, ip_address, save_startup)
                    if isinstance(output, dict) and "error" in output:
                        error_msg = f"{output['error']}: {output['message']}"
                        if "available_interfaces" in output:
                            interfaces_output = html.unescape(output['available_interfaces'])
                            error_msg += f"\n\nAvailable interfaces:\n{interfaces_output}"
                        flash(error_msg, 'danger')
                        return render_template('initialization.html', error=error_msg, 
                                            available_ports=get_available_ports())

                return render_template('initialization.html', success="Device successfully initialized!", available_ports=get_available_ports())

            except Exception as e:
                return render_template('initialization.html', error=f"An error occurred: {e}", available_ports=get_available_ports())

        return render_template('initialization.html', available_ports=get_available_ports())

    return device_init_bp