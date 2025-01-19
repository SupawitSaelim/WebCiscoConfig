from flask import Blueprint, render_template, request, redirect, url_for
from pymongo.errors import ServerSelectionTimeoutError
import threading
from device_config import configure_etherchannel

aggregation_routes = Blueprint('aggregation_routes', __name__)

def init_aggregation_routes(device_collection):
    @aggregation_routes.route('/etherchannel', methods=['GET'])
    def etherchannel():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
        return render_template('etherchannel.html', cisco_devices=cisco_devices)

    @aggregation_routes.route('/etherchannel_settings', methods=['POST'])
    def etherchannel_settings():
        device_name = request.form.get("device_name")
        many_hostname = request.form.get("many_hostname")
        etherchannel_interfaces = request.form.get("etherchannel_interfaces")
        channel_group_number = request.form.get("channel_group_number")
        pagp_mode = request.form.getlist("pagp_mode")

        etherchannel_interfaces_lacp = request.form.get("etherchannel_interfaces_lacp")
        channel_group_number_lacp = request.form.get("channel_group_number_lacp")
        lacp_mode = request.form.getlist("lacp_mode")

        etherchannel_interfaces_lacp_delete = request.form.get("etherchannel_interfaces_lacp_delete")

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
                    target=configure_etherchannel, 
                    args=(device, etherchannel_interfaces, channel_group_number, pagp_mode,
                          etherchannel_interfaces_lacp, channel_group_number_lacp, lacp_mode,
                          etherchannel_interfaces_lacp_delete)
                )
                threads.append(thread)
                thread.start()

        for thread in threads:
            thread.join()

        return redirect(url_for('aggregation_routes.etherchannel'))

    return aggregation_routes
