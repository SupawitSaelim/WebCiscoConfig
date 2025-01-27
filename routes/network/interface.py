from flask import Blueprint, render_template, request, redirect, url_for, flash
from pymongo.errors import ServerSelectionTimeoutError
import threading
from core.device.device_config import configure_network_interface
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException

network_interface = Blueprint('network_interface', __name__)

def init_network_interface(device_collection):
    @network_interface.route('/network_interface_page', methods=['GET'])
    def network_interface_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
            flash("Database connection error. Please try again later.", "danger")
        return render_template('network_interface_config.html', cisco_devices=cisco_devices)

    @network_interface.route('/network_interface_settings', methods=['GET', 'POST'])
    def network_interface_settings():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
            flash("Database connection error. Please try again later.", "danger")
            return redirect(url_for('network_interface.network_interface_page'))

        if request.method == 'POST':
            device_name = request.form.get('device_name')
            many_hostname = request.form.get('many_hostname')
            
            # ข้อมูล IPv4
            interfaces_ipv4 = request.form.get('interfaces_ipv4')
            config_type = request.form.get('config_type')
            dhcp_ipv4 = (config_type == 'dhcp_ipv4')
            ip_address_ipv4 = request.form.get('ip_address_ipv4')
            subnet_mask_ipv4 = request.form.get('subnet_mask_ipv4')
            enable_ipv4 = request.form.get('enable_ipv4') == 'on'
            disable_ipv4 = request.form.get('disable_ipv4') == 'on'
            delete_ipv4 = request.form.get('delete_ipv4') == 'on'
            
            # ข้อมูล IPv6
            interfaces_ipv6 = request.form.get('interfaces_ipv6')
            dhcp_ipv6 = request.form.get('config_type_ipv6') == 'dhcp_ipv6'
            ip_address_ipv6 = request.form.get('ip_address_ipv6')
            enable_ipv6 = request.form.get('enable_ipv6') == 'on'
            disable_ipv6 = request.form.get('disable_ipv6') == 'on'
            delete_ipv6 = request.form.get('delete_ipv6') == 'on'

            # ข้อมูล Speed/Duplex
            interfaces_du = request.form.get('interfaces_du')
            speed_duplex = request.form.get('speed_duplex')
            
            device_ips = []
            device_names_processed = set()
            configuration_results = []

            try:
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
                                flash(f"Duplicate IP detected for device {name} with IP {ip_address}", "danger")
                                return redirect(url_for('network_interface.network_interface_page'))
                        
                        if not found_any:
                            flash(f"Device {name} not found in database", "danger")
                            return redirect(url_for('network_interface.network_interface_page'))
                        
                        device_names_processed.add(name)

                # Process single device
                elif device_name:
                    device = device_collection.find_one({"device_info.ip": device_name})
                    if device:
                        device_ips.append(device["device_info"]["ip"])
                    else:
                        flash(f"Device with IP {device_name} not found in database", "danger")
                        return redirect(url_for('network_interface.network_interface_page'))

                threads = []
                results = []

                for ip in device_ips:
                    device = device_collection.find_one({"device_info.ip": ip})
                    if device:
                        result = {'ip': ip, 'status': None, 'error': None}
                        results.append(result)
                        
                        thread = threading.Thread(
                            target=configure_network_interface_with_status,
                            args=(device, interfaces_ipv4, dhcp_ipv4, ip_address_ipv4,
                                  subnet_mask_ipv4, enable_ipv4, disable_ipv4, delete_ipv4,
                                  interfaces_ipv6, dhcp_ipv6, ip_address_ipv6, enable_ipv6,
                                  disable_ipv6, delete_ipv6, interfaces_du, speed_duplex,
                                  device_collection, result)
                        )
                        threads.append(thread)
                        thread.start()

                # Wait for all configurations to complete
                for thread in threads:
                    thread.join()

                # Process results
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

            return redirect(url_for('network_interface.network_interface_page'))

        return render_template('network_interface_config.html', cisco_devices=cisco_devices)

    return network_interface

def configure_network_interface_with_status(device, *args):
    """Wrapper function for configure_network_interface that handles status updates"""
    try:
        configure_network_interface(device, *args[:-1])  # ส่งทุก argument ยกเว้น result
        args[-1]['status'] = 'success'  # result เป็น argument สุดท้าย
    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        error_message = str(e)
        if "TCP connection to device failed" in error_message:
            error_message = ("TCP connection to device failed. Common causes: "
                           "1. Incorrect hostname or IP address. "
                           "2. Wrong TCP port. "
                           "3. Intermediate firewall blocking access.")
        args[-1]['status'] = 'failed'
        args[-1]['error'] = error_message
    except Exception as e:
        error_message = str(e)
        if "Pattern not detected:" in error_message:
            error_message = "Unable to access privileged mode (#). Please ensure your enable password or secret password is correct."
        args[-1]['status'] = 'failed'
        args[-1]['error'] = error_message