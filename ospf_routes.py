from flask import Blueprint, render_template, request, redirect, url_for, flash
from pymongo.errors import ServerSelectionTimeoutError
import threading
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException
from routing_config import configure_ospf_route

ospf_routes = Blueprint('ospf_routes', __name__)

def init_ospf_routes(device_collection):
    @ospf_routes.route('/ospf_page', methods=['GET'])
    def ospf_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
            flash("Database connection error. Please try again later.", "danger")
        return render_template('ospf.html', cisco_devices=cisco_devices)

    @ospf_routes.route('/ospf_settings', methods=['POST'])
    def ospf_settings():
        try:
            # Get form data
            device_name = request.form.get("device_name")
            many_hostname = request.form.get("many_hostname")
            
            # OSPF settings
            destination_networks = request.form.getlist("destination_networks[]")
            ospf_areas = request.form.getlist("ospf_areas[]")
            process_id = request.form.get("process_id")
            router_id = request.form.get("router_id")
            
            # Remove settings
            remove_destination_networks = request.form.getlist("remove_destination_networks[]")
            remove_ospf_areas = request.form.getlist("remove_ospf_areas[]")
            delete_process_id = request.form.get("delete_process_id")
            process_id_input = request.form.get("process_id_input")

            if not delete_process_id:
                process_id_input = None

            # Validate inputs
            if not (device_name or many_hostname):
                flash("Please select at least one device.", "danger")
                return redirect(url_for('ospf_routes.ospf_page'))

            if not any([destination_networks, process_id, delete_process_id]):
                flash("Please specify at least one OSPF configuration.", "danger")
                return redirect(url_for('ospf_routes.ospf_page'))

            if destination_networks and ospf_areas and len(destination_networks) != len(ospf_areas):
                flash("Number of networks must match number of areas.", "danger")
                return redirect(url_for('ospf_routes.ospf_page'))

            if remove_destination_networks and len(remove_destination_networks) != len(remove_ospf_areas):
                flash("Number of remove networks must match number of remove areas.", "danger")
                return redirect(url_for('ospf_routes.ospf_page'))

            device_ips = []
            device_names_processed = set()

            # Process single device
            if device_name:
                device = device_collection.find_one({"device_info.ip": device_name})
                if device:
                    device_ips.append(device["device_info"]["ip"])
                else:
                    flash(f"Device with IP {device_name} not found in database", "danger")
                    return redirect(url_for('ospf_routes.ospf_page'))

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
                            return redirect(url_for('ospf_routes.ospf_page'))
                    else:
                        flash(f"Device {name} not found in database", "danger")
                        return redirect(url_for('ospf_routes.ospf_page'))
                    
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
                        target=configure_ospf_route_with_status,
                        args=(device, process_id, destination_networks, ospf_areas, router_id,
                              remove_destination_networks, remove_ospf_areas, delete_process_id,
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
                flash(f"OSPF configuration successful for devices: {', '.join(success_devices)}", "success")
            
            if failed_devices:
                for device in failed_devices:
                    flash(f"OSPF configuration failed for {device}", "danger")

        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "danger")

        return redirect(url_for('ospf_routes.ospf_page'))

    return ospf_routes

def configure_ospf_route_with_status(device, process_id, destination_networks, ospf_areas, router_id,
                                   remove_destination_networks, remove_ospf_areas, delete_process_id,
                                   process_id_input, result):
    """
    Wrapper function for configure_ospf_route that handles status updates
    """
    try:
        configure_ospf_route(device, process_id, destination_networks, ospf_areas, router_id,
                           remove_destination_networks, remove_ospf_areas, delete_process_id,
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