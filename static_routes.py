from flask import Blueprint, render_template, request, redirect, url_for
from pymongo.errors import ServerSelectionTimeoutError
import threading
from routing_config import configure_static_route

static_routes = Blueprint('static_routes', __name__)

def init_static_routes(device_collection):
    @static_routes.route('/static_page', methods=['GET'])
    def static_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
        return render_template('static.html', cisco_devices=cisco_devices)

    @static_routes.route('/static_settings', methods=['POST'])
    def static_settings():
        device_name = request.form.get("device_name")
        many_hostname = request.form.get("many_hostname")
        destination_networks = request.form.getlist("destination_networks[]")
        exit_interfaces_or_next_hops = request.form.getlist("exit_interfaces_or_next_hops[]")

        default_route = request.form.get("default_route")
        remove_default = request.form.get("remove_default")

        remove_destination_networks = request.form.getlist("remove_destination_networks[]")
        remove_exit_interfaces_or_next_hops = request.form.getlist("remove_exit_interfaces_or_next_hops[]")
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
                    target=configure_static_route,
                    args=(device, destination_networks, exit_interfaces_or_next_hops,
                          default_route, remove_default, remove_destination_networks,
                          remove_exit_interfaces_or_next_hops)
                )
                threads.append(thread)
                thread.start()

        for thread in threads:
            thread.join()

        return redirect(url_for('static_routes.static_page'))

    return static_routes
