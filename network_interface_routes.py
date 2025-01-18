from flask import Blueprint, render_template, request, redirect, url_for,flash
from pymongo.errors import ServerSelectionTimeoutError
import threading
from device_config import configure_network_interface

network_interface = Blueprint('network_interface', __name__)

def init_network_interface(device_collection):
    @network_interface.route('/network_interface_page', methods=['GET'])
    def network_interface_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
        return render_template('network_interface_config.html', cisco_devices=cisco_devices)

    @network_interface.route('/network_interface_settings', methods=['GET', 'POST'])
    def network_interface_settings():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None

        if request.method == 'POST':
            # รับค่าจากฟอร์ม
            device_name = request.form.get('device_name')
            many_hostname = request.form.get('many_hostname')
            
            # ข้อมูล IPv4
            interfaces_ipv4 = request.form.get('interfaces_ipv4')
            config_type = request.form.get('config_type')
            dhcp_ipv4 = (config_type == 'dhcp_ipv4')
            ip_address_ipv4 = request.form.get('ip_address_ipv4')
            subnet_mask_ipv4 = request.form.get('subnet_mask_ipv4')
            enable_ipv4 = request.form.get('enable_ipv4') == 'on'
            disable_ipv4 = request.form.get('disable_ipv4') == 'on'
            delete_ipv4 = request.form.get('delete_ipv4') == 'on'
            
            # ข้อมูล IPv6
            interfaces_ipv6 = request.form.get('interfaces_ipv6')
            dhcp_ipv6 = request.form.get('config_type_ipv6') == 'dhcp_ipv6'
            ip_address_ipv6 = request.form.get('ip_address_ipv6')
            enable_ipv6 = request.form.get('enable_ipv6') == 'on'
            disable_ipv6 = request.form.get('disable_ipv6') == 'on'
            delete_ipv6 = request.form.get('delete_ipv6') == 'on'

            # ข้อมูล Speed/Duplex
            interfaces_du = request.form.get('interfaces_du')
            speed_duplex = request.form.get('speed_duplex')
            
            device_ips = []
            device_names_processed = set()

            # จัดการกับหลาย hostname
            if many_hostname:
                device_names = [name.strip() for name in many_hostname.split(',')]
                for name in device_names:
                    if name in device_names_processed:
                        continue

                    devices = device_collection.find({"name": name})
                    found_any = False

                    for device in devices:
                        ip_address = device["device_info"]["ip"]
                        if ip_address not in device_ips:
                            device_ips.append(ip_address)
                            found_any = True
                        else:
                            return f'<script>alert("Duplicate IP detected for device {name} with IP {ip_address}"); window.location.href="/network_interface_page";</script>'

                    if not found_any:
                        return f'<script>alert("Device {name} not found in database"); window.location.href="/network_interface_page";</script>'
                    
                    device_names_processed.add(name)

            # จัดการกับ single device
            elif device_name:
                device = device_collection.find_one({"device_info.ip": device_name})
                if device:
                    device_ips.append(device["device_info"]["ip"])
                else:
                    return f'<script>alert("Device with IP {device_name} not found in database"); window.location.href="/network_interface_page";</script>'

            threads = []
            print("Device IPs to configure:", device_ips)
            
            # ดำเนินการกับแต่ละอุปกรณ์
            for ip in device_ips:
                device = device_collection.find_one({"device_info.ip": ip})
                
                if device:
                    thread = threading.Thread(
                        target=configure_network_interface,
                        args=(
                            device,
                            interfaces_ipv4,
                            dhcp_ipv4,
                            ip_address_ipv4,
                            subnet_mask_ipv4,
                            enable_ipv4,
                            disable_ipv4,
                            delete_ipv4,
                            interfaces_ipv6,
                            dhcp_ipv6,
                            ip_address_ipv6,
                            enable_ipv6,
                            disable_ipv6,
                            delete_ipv6,
                            interfaces_du,
                            speed_duplex,
                            device_collection
                        )
                    )
                    threads.append(thread)
                    thread.start()
                else:
                    return f'<script>alert("Device with IP {ip} not found in database"); window.location.href="/network_interface_page";</script>'
            
            for thread in threads:
                thread.join()
            
            flash("Configuration successful for devices: " + ", ".join(device_ips), "success")
            return redirect(url_for('network_interface.network_interface_page'))

        return render_template('network_interface_config.html', cisco_devices=cisco_devices)

    return network_interface