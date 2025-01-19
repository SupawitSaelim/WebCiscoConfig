from flask import Blueprint, render_template, request, redirect, url_for, flash
from pymongo.errors import ServerSelectionTimeoutError
import threading
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException
from routing_config import configure_eigrp_route

eigrp_routes = Blueprint('eigrp_routes', __name__)

def configure_eigrp_route_with_status(device, process_id, router_id, destination_networks,
                                    remove_destination_networks, delete_process_id,
                                    process_id_input, result):
    """
    Wrapper function for configure_eigrp_route that handles status updates
    """
    try:
        configure_eigrp_route(device, process_id, router_id, destination_networks,
                            remove_destination_networks, delete_process_id,
                            process_id_input)
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

def init_eigrp_routes(device_collection):
    @eigrp_routes.route('/eigrp_page', methods=['GET'])
    def eigrp_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
            flash("Database connection error. Please try again later.", "danger")
        return render_template('eigrp.html', cisco_devices=cisco_devices)

    @eigrp_routes.route('/eigrp_settings', methods=['POST'])
    def eigrp_settings():
        try:
            device_name = request.form.get("device_name")
            many_hostname = request.form.get("many_hostname")

            process_id = request.form.get("process_id")
            router_id = request.form.get("router_id")
            destination_networks = request.form.getlist("destination_networks[]")
            remove_destination_networks = request.form.getlist("remove_destination_networks[]")
            delete_process_id = request.form.get("delete_process_id")
            process_id_input = request.form.get("process_id_input")

            # Validate inputs
            if not (device_name or many_hostname):
                flash("Please select at least one device.", "danger")
                return redirect(url_for('eigrp_routes.eigrp_page'))

            if not any([process_id, delete_process_id]):
                flash("Please specify either a process ID or select delete process ID.", "danger")
                return redirect(url_for('eigrp_routes.eigrp_page'))

            if delete_process_id and not process_id_input:
                flash("Please specify process ID(s) to delete.", "danger")
                return redirect(url_for('eigrp_routes.eigrp_page'))

            device_ips = []
            device_names_processed = set()

            # Process single device
            if device_name:
                device = device_collection.find_one({"device_info.ip": device_name})
                if device:
                    device_ips.append(device["device_info"]["ip"])
                else:
                    flash(f"Device with IP {device_name} not found in database", "danger")
                    return redirect(url_for('eigrp_routes.eigrp_page'))

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
                            return redirect(url_for('eigrp_routes.eigrp_page'))
                    else:
                        flash(f"Device {name} not found in database", "danger")
                        return redirect(url_for('eigrp_routes.eigrp_page'))
                    
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
                        target=configure_eigrp_route_with_status,
                        args=(device, process_id, router_id, destination_networks,
                              remove_destination_networks, delete_process_id,
                              process_id_input, result)
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
                flash(f"EIGRP configuration successful for devices: {', '.join(success_devices)}", "success")
            
            if failed_devices:
                for device in failed_devices:
                    flash(f"EIGRP configuration failed for {device}", "danger")

        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "danger")

        return redirect(url_for('eigrp_routes.eigrp_page'))

    return eigrp_routes