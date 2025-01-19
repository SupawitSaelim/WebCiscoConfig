from flask import Blueprint, render_template, request, redirect, url_for, flash
from pymongo.errors import ServerSelectionTimeoutError
import threading
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException
from device_config import configure_etherchannel

aggregation_routes = Blueprint('aggregation_routes', __name__)

def init_aggregation_routes(device_collection):
    @aggregation_routes.route('/etherchannel', methods=['GET'])
    def etherchannel():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
            flash("Database connection error. Please try again later.", "danger")
        return render_template('etherchannel.html', cisco_devices=cisco_devices)

    @aggregation_routes.route('/etherchannel_settings', methods=['POST'])
    def etherchannel_settings():
        try:
            # Get form data
            device_name = request.form.get("device_name")
            many_hostname = request.form.get("many_hostname")
            
            # PAgP settings
            etherchannel_interfaces = request.form.get("etherchannel_interfaces")
            channel_group_number = request.form.get("channel_group_number")
            pagp_mode = request.form.getlist("pagp_mode")
            
            # LACP settings
            etherchannel_interfaces_lacp = request.form.get("etherchannel_interfaces_lacp")
            channel_group_number_lacp = request.form.get("channel_group_number_lacp")
            lacp_mode = request.form.getlist("lacp_mode")
            
            # Delete settings
            etherchannel_interfaces_lacp_delete = request.form.get("etherchannel_interfaces_lacp_delete")

            # Validate inputs
            if not (device_name or many_hostname):
                flash("Please select at least one device.", "danger")
                return redirect(url_for('aggregation_routes.etherchannel'))

            if not any([etherchannel_interfaces, etherchannel_interfaces_lacp, etherchannel_interfaces_lacp_delete]):
                flash("Please specify at least one interface configuration.", "danger")
                return redirect(url_for('aggregation_routes.etherchannel'))

            device_ips = []
            device_names_processed = set()

            # Process single device
            if device_name:
                device = device_collection.find_one({"device_info.ip": device_name})
                if device:
                    device_ips.append(device["device_info"]["ip"])
                else:
                    flash(f"Device with IP {device_name} not found in database", "danger")
                    return redirect(url_for('aggregation_routes.etherchannel'))

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
                            return redirect(url_for('aggregation_routes.etherchannel'))
                    else:
                        flash(f"Device {name} not found in database", "danger")
                        return redirect(url_for('aggregation_routes.etherchannel'))
                    
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
                        target=configure_etherchannel_with_status,
                        args=(device, etherchannel_interfaces, channel_group_number,
                              pagp_mode, etherchannel_interfaces_lacp,
                              channel_group_number_lacp, lacp_mode,
                              etherchannel_interfaces_lacp_delete, result)
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
                flash(f"EtherChannel configuration successful for devices: {', '.join(success_devices)}", "success")
            
            if failed_devices:
                for device in failed_devices:
                    flash(f"EtherChannel configuration failed for {device}", "danger")

        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "danger")

        return redirect(url_for('aggregation_routes.etherchannel'))

    return aggregation_routes

def configure_etherchannel_with_status(device, etherchannel_interfaces, channel_group_number,
                                     pagp_mode, etherchannel_interfaces_lacp,
                                     channel_group_number_lacp, lacp_mode,
                                     etherchannel_interfaces_lacp_delete, result):
    """
    Wrapper function for configure_etherchannel that handles status updates
    """
    try:
        configure_etherchannel(device, etherchannel_interfaces, channel_group_number,
                             pagp_mode, etherchannel_interfaces_lacp,
                             channel_group_number_lacp, lacp_mode,
                             etherchannel_interfaces_lacp_delete)
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