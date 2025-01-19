from flask import Blueprint, render_template, request, redirect, url_for, flash
from pymongo.errors import ServerSelectionTimeoutError
import threading
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException
from routing_config import configure_static_route

static_routes = Blueprint('static_routes', __name__)

def init_static_routes(device_collection):
    @static_routes.route('/static_page', methods=['GET'])
    def static_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
            flash("Database connection error. Please try again later.", "danger")
        return render_template('static.html', cisco_devices=cisco_devices)

    @static_routes.route('/static_settings', methods=['POST'])
    def static_settings():
        try:
            # Get form data
            device_name = request.form.get("device_name")
            many_hostname = request.form.get("many_hostname")
            
            # Static route settings
            destination_networks = request.form.getlist("destination_networks[]")
            exit_interfaces_or_next_hops = request.form.getlist("exit_interfaces_or_next_hops[]")
            
            # Default route settings
            default_route = request.form.get("default_route")
            remove_default = request.form.get("remove_default")
            
            # Remove route settings
            remove_destination_networks = request.form.getlist("remove_destination_networks[]")
            remove_exit_interfaces_or_next_hops = request.form.getlist("remove_exit_interfaces_or_next_hops[]")

            # Validate inputs
            if not (device_name or many_hostname):
                flash("Please select at least one device.", "danger")
                return redirect(url_for('static_routes.static_page'))

            if not any([destination_networks, default_route, remove_destination_networks]):
                flash("Please specify at least one route configuration.", "danger")
                return redirect(url_for('static_routes.static_page'))

            if len(destination_networks) != len(exit_interfaces_or_next_hops):
                flash("Number of destination networks must match number of exit interfaces/next hops.", "danger")
                return redirect(url_for('static_routes.static_page'))

            if remove_destination_networks and len(remove_destination_networks) != len(remove_exit_interfaces_or_next_hops):
                flash("Number of remove destination networks must match number of remove exit interfaces/next hops.", "danger")
                return redirect(url_for('static_routes.static_page'))

            device_ips = []
            device_names_processed = set()

            # Process single device
            if device_name:
                device = device_collection.find_one({"device_info.ip": device_name})
                if device:
                    device_ips.append(device["device_info"]["ip"])
                else:
                    flash(f"Device with IP {device_name} not found in database", "danger")
                    return redirect(url_for('static_routes.static_page'))

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
                            return redirect(url_for('static_routes.static_page'))
                    else:
                        flash(f"Device {name} not found in database", "danger")
                        return redirect(url_for('static_routes.static_page'))
                    
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
                        target=configure_static_route_with_status,
                        args=(device, destination_networks, exit_interfaces_or_next_hops,
                              default_route, remove_default, remove_destination_networks,
                              remove_exit_interfaces_or_next_hops, result)
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
                flash(f"Static route configuration successful for devices: {', '.join(success_devices)}", "success")
            
            if failed_devices:
                for device in failed_devices:
                    flash(f"Static route configuration failed for {device}", "danger")

        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "danger")

        return redirect(url_for('static_routes.static_page'))

    return static_routes

def configure_static_route_with_status(device, destination_networks, exit_interfaces_or_next_hops,
                                     default_route, remove_default, remove_destination_networks,
                                     remove_exit_interfaces_or_next_hops, result):
    """
    Wrapper function for configure_static_route that handles status updates
    """
    try:
        configure_static_route(device, destination_networks, exit_interfaces_or_next_hops,
                             default_route, remove_default, remove_destination_networks,
                             remove_exit_interfaces_or_next_hops)
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