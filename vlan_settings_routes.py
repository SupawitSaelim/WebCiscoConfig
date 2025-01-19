from flask import Blueprint, render_template, request, redirect, url_for, flash
from pymongo.errors import ServerSelectionTimeoutError
import threading
from device_config import manage_vlan_on_device
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException

vlan_settings_bp = Blueprint('vlan_settings', __name__)

def init_vlan_settings(device_collection):
    @vlan_settings_bp.route('/vlan_settings_page', methods=['GET'])
    def vlan_settings_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
            flash("Database connection error. Please try again later.", "danger")  
        return render_template('vlan_management.html', cisco_devices=cisco_devices)

    @vlan_settings_bp.route('/vlan_settings', methods=['GET', 'POST'])
    def vlan_settings():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
            flash("Database connection error. Please try again later.", "danger")
            return redirect(url_for('vlan_settings.vlan_settings_page'))

        if request.method == 'POST':
            device_name = request.form.get('device_name')  
            many_hostname = request.form.get('many_hostname')  
            vlan_id = request.form.get('vlan_id')
            vlan_id_del = request.form.get('vlan_id_del')  

            vlan_ids_to_change = request.form.getlist('vlan_ids_change[]')
            vlan_names_to_change = request.form.getlist('vlan_names_change[]')

            enable_vlans = request.form.get('enable_vlans')  
            disable_vlans = request.form.get('disable_vlans')  
            vlan_id_enable = request.form.get('vlan_id_enable')  
            vlan_id_disable = request.form.get('vlan_id_disable')
            del_vlan_dat = request.form.get('del_vlan_dat')  

            access_vlans = request.form.get('access_vlans')
            access_interface = request.form.get('access_interface')
            access_vlan_id = request.form.get('access_vlan_id')
            disable_dtp = request.form.get('disable_dtp')  

            trunk_ports = request.form.get('trunk_ports')
            trunk_mode_select = request.form.get('trunk_mode_select')
            trunk_interface = request.form.get('trunk_interface')
            trunk_native = request.form.get('trunk_native')
            allow_vlan = request.form.get('allow_vlan')

            device_ips = []
            device_names_processed = set()

            vlan_range = []
            if vlan_id:
                vlan_entries = vlan_id.split(',')
                for entry in vlan_entries:
                    entry = entry.strip()
                    if '-' in entry:
                        try:
                            start_vlan, end_vlan = entry.split('-')
                            vlan_range.extend(range(int(start_vlan), int(end_vlan) + 1))
                        except ValueError:
                            return f'<script>alert("Invalid VLAN range: {entry}"); window.location.href="/vlan_settings";</script>'
                    else:
                        try:
                            vlan_range.append(int(entry))
                        except ValueError:
                            return f'<script>alert("Invalid VLAN ID: {entry}"); window.location.href="/vlan_settings";</script>'
            
            vlan_range_del = []
            if vlan_id_del:
                vlan_entries_del = vlan_id_del.split(',')
                for entry in vlan_entries_del:
                    entry = entry.strip()
                    if '-' in entry:
                        try:
                            start_vlan, end_vlan = entry.split('-')
                            vlan_range_del.extend(range(int(start_vlan), int(end_vlan) + 1))
                        except ValueError:
                            return f'<script>alert("Invalid VLAN delete range: {entry}"); window.location.href="/vlan_settings";</script>'
                    else:
                        try:
                            vlan_range_del.append(int(entry))
                        except ValueError:
                            return f'<script>alert("Invalid VLAN delete ID: {entry}"); window.location.href="/vlan_settings";</script>'
            
            vlan_changes = []
            for vlan_id, vlan_name in zip(vlan_ids_to_change, vlan_names_to_change):
                vlan_changes.append((vlan_id.strip(), vlan_name.strip()))

            vlan_range_enable = []
            if enable_vlans and vlan_id_enable:
                vlan_entries_enable = vlan_id_enable.split(',')
                for entry in vlan_entries_enable:
                    entry = entry.strip()
                    if '-' in entry:  
                        try:
                            start_vlan, end_vlan = entry.split('-')
                            vlan_range_enable.extend(range(int(start_vlan), int(end_vlan) + 1)) 
                        except ValueError:
                            return f'<script>alert("Invalid VLAN range for Enable: {entry}"); window.location.href="/vlan_settings";</script>'
                    else:  
                        try:
                            vlan_range_enable.append(int(entry))
                        except ValueError:
                            return f'<script>alert("Invalid VLAN ID for Enable: {entry}"); window.location.href="/vlan_settings";</script>'

            vlan_range_disable = []
            if disable_vlans and vlan_id_disable:
                vlan_entries_disable = vlan_id_disable.split(',')
                for entry in vlan_entries_disable:
                    entry = entry.strip()
                    if '-' in entry:  
                        try:
                            start_vlan, end_vlan = entry.split('-')
                            vlan_range_disable.extend(range(int(start_vlan), int(end_vlan) + 1))  
                        except ValueError:
                            return f'<script>alert("Invalid VLAN range for Disable: {entry}"); window.location.href="/vlan_settings";</script>'
                    else:  
                        try:
                            vlan_range_disable.append(int(entry))
                        except ValueError:
                            return f'<script>alert("Invalid VLAN ID for Disable: {entry}"); window.location.href="/vlan_settings";</script>'

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
                            print(f"Duplicate IP detected for device {name} with IP {ip_address}")
                            return f'<script>alert("Duplicate IP detected for device {name} with IP {ip_address}"); window.location.href="/vlan_settings";</script>'

                    if not found_any:
                        print(f"Device {name} not found in database")
                        return f'<script>alert("Device {name} not found in database"); window.location.href="/vlan_settings";</script>'

                    device_names_processed.add(name)

            elif device_name:
                device = device_collection.find_one({"device_info.ip": device_name})
                if device:
                    device_ips.append(device["device_info"]["ip"])
                else:
                    print(f"Device with IP {device_name} not found in database")
                    return f'<script>alert("Device with IP {device_name} not found in database"); window.location.href="/vlan_settings";</script>'

            threads = []
            results = []
            for ip in device_ips:
                device = device_collection.find_one({"device_info.ip": ip})
                if device:
                    result = {'ip': ip, 'status': None, 'error': None}
                    results.append(result)
                    
                    thread = threading.Thread(
                        target=configure_vlan_with_status,
                        args=(device, vlan_range, vlan_range_del, vlan_changes, 
                              vlan_range_enable, vlan_range_disable, access_vlans, 
                              access_interface, access_vlan_id, disable_dtp, 
                              trunk_ports, trunk_mode_select, trunk_interface, 
                              trunk_native, allow_vlan, del_vlan_dat, result)
                    )
                    threads.append(thread)
                    thread.start()

            for thread in threads:
                thread.join()
            
            success_devices = []
            failed_devices = []

            for result in results:
                if result['status'] == 'success':
                    success_devices.append(result['ip'])
                else:
                    failed_devices.append(f"{result['ip']}: {result['error']}")

            if success_devices:
                flash(f"Configuration successful for devices: {', '.join(success_devices)}", "success")
            
            if failed_devices:
                for device in failed_devices:
                    flash(f"Configuration failed for {device}", "danger")

            return redirect(url_for('vlan_settings.vlan_settings_page'))

        return render_template('vlan_management.html', cisco_devices=cisco_devices)

    return vlan_settings_bp

def configure_vlan_with_status(device, *args):
    """Wrapper function for manage_vlan_on_device that handles status updates"""
    try:
        manage_vlan_on_device(device, *args[:-1])  # Send all arguments except result
        args[-1]['status'] = 'success'  # Result is the last argument
    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        error_message = str(e)
        if "TCP connection to device failed" in error_message:
            error_message = ("TCP connection to device failed. Common causes: "
                           "1. Incorrect hostname or IP address. "
                           "2. Wrong TCP port. "
                           "3. Intermediate firewall blocking access.")
        args[-1]['status'] = 'failed'
        args[-1]['error'] = error_message
    except Exception as e:
        args[-1]['status'] = 'failed'
        args[-1]['error'] = str(e)