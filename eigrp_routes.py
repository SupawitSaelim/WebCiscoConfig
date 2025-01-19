from flask import Blueprint, render_template, request, redirect, url_for
from pymongo.errors import ServerSelectionTimeoutError
import threading
from routing_config import configure_eigrp_route

eigrp_routes = Blueprint('eigrp_routes', __name__)

def init_eigrp_routes(device_collection):
    @eigrp_routes.route('/eigrp_page', methods=['GET'])
    def eigrp_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None  
        return render_template('eigrp.html', cisco_devices=cisco_devices)

    @eigrp_routes.route('/eigrp_settings', methods=['POST'])
    def eigrp_settings():
        device_name = request.form.get("device_name")
        many_hostname = request.form.get("many_hostname")

        process_id = request.form.get("process_id")
        router_id = request.form.get("router_id")
        destination_networks = request.form.getlist("destination_networks[]")
        remove_destination_networks = request.form.getlist("remove_destination_networks[]")
        delete_process_id = request.form.get("delete_process_id")
        process_id_input = request.form.get("process_id_input")

        if not delete_process_id:
            process_id_input = None

        device_ips = []
        if device_name:
            device = device_collection.find_one({"device_info.ip": device_name})
            if device:
                device_ips.append(device["device_info"]["ip"])
            else:
                return f'<script>alert("Device with IP {device_name} not found in database"); window.location.href="/eigrp_page";</script>'

        if many_hostname:
            for host in many_hostname.split(','):
                device = device_collection.find_one({"name": host.strip()})
                if device:
                    device_ips.append(device["device_info"]["ip"])
                else:
                    return f'<script>alert("Device {host} not found in database"); window.location.href="/eigrp_page";</script>'

        threads = []
        for ip in device_ips:
            device = device_collection.find_one({"device_info.ip": ip})
            if device:
                thread = threading.Thread(
                    target=configure_eigrp_route,
                    args=(device, process_id, router_id, destination_networks, 
                          remove_destination_networks, delete_process_id, 
                          process_id_input)
                )
                threads.append(thread)
                thread.start()

        for thread in threads:
            thread.join()

        return redirect(url_for('eigrp_routes.eigrp_page'))

    return eigrp_routes
