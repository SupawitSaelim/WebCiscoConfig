from flask import Blueprint, render_template, request, redirect, url_for, flash
from pymongo.errors import ServerSelectionTimeoutError
import threading
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException
from core.device.device_config import configure_spanning_tree

stp_bp = Blueprint('stp', __name__)

def init_stp_routes(device_collection):
    @stp_bp.route('/stp_page', methods=['GET'])
    def stp_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
            flash("Database connection error. Please try again later.", "danger")
        return render_template('stp.html', cisco_devices=cisco_devices)

    @stp_bp.route('/stp_settings', methods=['POST'])
    def stp_settings():
        try:
            device_name = request.form.get("device_name")
            many_hostname = request.form.get("many_hostname")
            
            stp_mode = request.form.get("stp_mode")
            root_primary = request.form.get("root_primary") == "on"
            root_vlan_id = request.form.get("root_vlan_id") if root_primary else None
            
            root_secondary = request.form.get("root_secondary") == "on"
            root_secondary_vlan_id = request.form.get("root_secondary_vlan_id") if root_secondary else None
            
            portfast_enable = request.form.get("portfast_enable") == "on"
            portfast_disable = request.form.get("portfast_disable") == "on"
            portfast_int_enable = request.form.get("portfast_int_enable") if portfast_enable else None
            portfast_int_disable = request.form.get("portfast_int_disable") if portfast_disable else None

            device_ips = []
            device_names_processed = set()

            # Process single device
            if device_name:
                device = device_collection.find_one({"device_info.ip": device_name})
                if device:
                    device_ips.append(device["device_info"]["ip"])
                else:
                    flash(f"Device with IP {device_name} not found in database", "danger")
                    return redirect(url_for('stp.stp_page'))

            # Process multiple devices
            if many_hostname:
                device_names = [name.strip() for name in many_hostname.split(',')]
                for name in device_names:
                    if name in device_names_processed:
                        continue
                    
                    device = device_collection.find_one({"name": name})
                    if device:
                        ip_address = device["device_info"]["ip"]
                        if ip_address not in device_ips:
                            device_ips.append(ip_address)
                        else:
                            flash(f"Duplicate IP detected for device {name} with IP {ip_address}", "danger")
                            return redirect(url_for('stp.stp_page'))
                    else:
                        flash(f"Device {name} not found in database", "danger")
                        return redirect(url_for('stp.stp_page'))
                    
                    device_names_processed.add(name)

            # Configure devices and collect results
            threads = []
            results = []

            for ip in device_ips:
                device = device_collection.find_one({"device_info.ip": ip})
                if device:
                    result = {'ip': ip, 'name': device['name'], 'status': None, 'error': None}
                    results.append(result)
                    
                    thread = threading.Thread(
                        target=configure_spanning_tree_with_status,
                        args=(device, stp_mode, root_primary, root_vlan_id,
                              root_secondary, root_secondary_vlan_id,
                              portfast_enable, portfast_disable,
                              portfast_int_enable, portfast_int_disable,
                              result)
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
                    success_devices.append(result['name'])
                else:
                    failed_devices.append(f"{result['name']}: {result['error']}")

            if success_devices:
                flash(f"Spanning tree configuration successful for devices: {', '.join(success_devices)}", "success")
            
            if failed_devices:
                for device in failed_devices:
                    flash(f"Spanning tree configuration failed for {device}", "danger")

        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "danger")

        return redirect(url_for('stp.stp_page'))

    return stp_bp

def configure_spanning_tree_with_status(device, stp_mode, root_primary, root_vlan_id,
                                      root_secondary, root_secondary_vlan_id,
                                      portfast_enable, portfast_disable,
                                      portfast_int_enable, portfast_int_disable,
                                      result):
    """
    Wrapper function for configure_spanning_tree that handles status updates
    """
    try:
        configure_spanning_tree(device, stp_mode, root_primary, root_vlan_id,
                              root_secondary, root_secondary_vlan_id,
                              portfast_enable, portfast_disable,
                              portfast_int_enable, portfast_int_disable)
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
        result['status'] = 'failed'
        result['error'] = str(e)