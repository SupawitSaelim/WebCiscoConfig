from flask import Blueprint, render_template, request, redirect, url_for, flash
from pymongo.errors import ServerSelectionTimeoutError
import threading
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException
from routing_config import configure_rip_route

rip_routes = Blueprint('rip_routes', __name__)

def init_rip_routes(device_collection):
    @rip_routes.route('/rip_page', methods=['GET'])
    def rip_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
            flash("Database connection error. Please try again later.", "danger")
        return render_template('ripv2.html', cisco_devices=cisco_devices)

    @rip_routes.route('/rip_settings', methods=['POST'])
    def rip_settings():
        try:
            # Get form data
            device_name = request.form.get("device_name")
            many_hostname = request.form.get("many_hostname")
            
            # RIP configuration settings
            destination_networks = request.form.getlist("destination_networks[]")
            auto_summary = request.form.get("auto_summary")
            remove_destination_networks = request.form.getlist("remove_destination_networks[]")
            disable_rip = request.form.get("disable_rip")

            # Validate inputs
            if not (device_name or many_hostname):
                flash("Please select at least one device.", "danger")
                return redirect(url_for('rip_routes.rip_page'))

            if not any([destination_networks, auto_summary, remove_destination_networks, disable_rip]):
                flash("Please specify at least one RIP configuration option.", "danger")
                return redirect(url_for('rip_routes.rip_page'))

            device_ips = []
            device_names_processed = set()

            # Process single device
            if device_name:
                device = device_collection.find_one({"device_info.ip": device_name})
                if device:
                    device_ips.append(device["device_info"]["ip"])
                else:
                    flash(f"Device with IP {device_name} not found in database", "danger")
                    return redirect(url_for('rip_routes.rip_page'))

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
                            return redirect(url_for('rip_routes.rip_page'))
                    else:
                        flash(f"Device {name} not found in database", "danger")
                        return redirect(url_for('rip_routes.rip_page'))
                    
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
                        target=configure_rip_route_with_status,
                        args=(device, destination_networks, auto_summary,
                              remove_destination_networks, disable_rip, result)
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
                flash(f"RIP configuration successful for devices: {', '.join(success_devices)}", "success")
            
            if failed_devices:
                for device in failed_devices:
                    flash(f"RIP configuration failed for {device}", "danger")

        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "danger")

        return redirect(url_for('rip_routes.rip_page'))

    return rip_routes

def configure_rip_route_with_status(device, destination_networks, auto_summary,
                                  remove_destination_networks, disable_rip, result):
    """
    Wrapper function for configure_rip_route that handles status updates
    """
    try:
        configure_rip_route(device, destination_networks, auto_summary,
                          remove_destination_networks, disable_rip)
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