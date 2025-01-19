from flask import Blueprint, render_template, request, redirect, url_for
from pymongo.errors import ServerSelectionTimeoutError
import threading
from routing_config import configure_rip_route

rip_routes = Blueprint('rip_routes', __name__)

def init_rip_routes(device_collection):
    @rip_routes.route('/rip_page', methods=['GET'])
    def rip_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
        return render_template('ripv2.html', cisco_devices=cisco_devices)

    @rip_routes.route('/rip_settings', methods=['POST'])
    def rip_settings():
        device_name = request.form.get("device_name")
        many_hostname = request.form.get("many_hostname")

        destination_networks = request.form.getlist("destination_networks[]")
        auto_summary = request.form.get("auto_summary")
        remove_destination_networks = request.form.getlist("remove_destination_networks[]")
        disable_rip = request.form.get("disable_rip")

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
                    target=configure_rip_route,
                    args=(device, destination_networks, auto_summary, remove_destination_networks, disable_rip)
                )
                threads.append(thread)
                thread.start()

        for thread in threads:
            thread.join()

        return redirect(url_for('rip_routes.rip_page'))

    return rip_routes
