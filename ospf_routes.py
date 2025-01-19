from flask import Blueprint, render_template, request, redirect, url_for
from pymongo.errors import ServerSelectionTimeoutError
import threading
from routing_config import configure_ospf_route

ospf_routes = Blueprint('ospf_routes', __name__)

def init_ospf_routes(device_collection):
    @ospf_routes.route('/ospf_page', methods=['GET'])
    def ospf_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None  
        return render_template('ospf.html', cisco_devices=cisco_devices)

    @ospf_routes.route('/ospf_settings', methods=['POST'])
    def ospf_settings():
        device_name = request.form.get("device_name")
        many_hostname = request.form.get("many_hostname")

        destination_networks = request.form.getlist("destination_networks[]")
        ospf_areas = request.form.getlist("ospf_areas[]")
        process_id = request.form.get("process_id")
        router_id = request.form.get("router_id")

        remove_destination_networks = request.form.getlist("remove_destination_networks[]")
        remove_ospf_areas = request.form.getlist("remove_ospf_areas[]")
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
                return f'<script>alert("Device with IP {device_name} not found in database"); window.location.href="/management_settings_page";</script>'

        if many_hostname:
            for host in many_hostname.split(','):
                device = device_collection.find_one({"name": host.strip()})
                if device:
                    device_ips.append(device["device_info"]["ip"])
                else:
                    return f'<script>alert("Device {host} not found in database"); window.location.href="/management_settings_page";</script>'

        threads = []
        for ip in device_ips:
            device = device_collection.find_one({"device_info.ip": ip})
            if device:
                thread = threading.Thread(
                    target=configure_ospf_route,
                    args=(device, process_id, destination_networks, ospf_areas, router_id,
                          remove_destination_networks, remove_ospf_areas, delete_process_id,
                          process_id_input)
                )
                threads.append(thread)
                thread.start()

        for thread in threads:
            thread.join()

        return redirect(url_for('ospf_routes.ospf_page'))

    return ospf_routes
