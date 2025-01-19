from flask import Blueprint, render_template, request, redirect, url_for, flash
from pymongo.errors import ServerSelectionTimeoutError
import threading
from device_config import configure_spanning_tree

stp_bp = Blueprint('stp', __name__)

def init_stp_routes(device_collection):
    @stp_bp.route('/stp_page', methods=['GET'])
    def stp_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None  
        return render_template('stp.html', cisco_devices=cisco_devices)

    @stp_bp.route('/stp_settings', methods=['POST'])
    def stp_settings():
        device_name = request.form.get("device_name")
        many_hostname = request.form.get("many_hostname")

        stp_mode = request.form.get("stp_mode")
        root_primary = request.form.get("root_primary") == "on"
        root_vlan_id = request.form.get("root_vlan_id") if root_primary else None

        root_secondary = request.form.get("root_secondary") == "on"
        root_secondary_vlan_id = request.form.get("root_secondary_vlan_id") if root_secondary else None

        portfast_enable = request.form.get("portfast_enable") == "on"
        portfast_disable = request.form.get("portfast_disable") == "on"
        portfast_int_enable = request.form.get("portfast_int_enable") if portfast_enable else None
        portfast_int_disable = request.form.get("portfast_int_disable") if portfast_disable else None

        device_ips = []

        if device_name:
            device = device_collection.find_one({"device_info.ip": device_name})
            if device:
                device_ips.append(device["device_info"]["ip"])
            else:
                return f'<script>alert("Device with IP {device_name} not found in database"); window.location.href="/stp_page";</script>'

        if many_hostname:
            for host in many_hostname.split(','):
                device = device_collection.find_one({"name": host.strip()})
                if device:
                    device_ips.append(device["device_info"]["ip"])
                else:
                    return f'<script>alert("Device {host} not found in database"); window.location.href="/stp_page";</script>'

        threads = []
        for ip in device_ips:
            device = device_collection.find_one({"device_info.ip": ip})
            if device:
                thread = threading.Thread(
                    target=configure_spanning_tree,
                    args=(device, stp_mode, root_primary, root_vlan_id, root_secondary, root_secondary_vlan_id,
                          portfast_enable, portfast_disable, portfast_int_enable, portfast_int_disable)
                )
                threads.append(thread)
                thread.start()

        for thread in threads:
            thread.join()

        return redirect(url_for('stp.stp_page'))

    return stp_bp
