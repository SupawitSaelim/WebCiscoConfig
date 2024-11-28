from flask import Flask, render_template, request, redirect, url_for, flash,jsonify
from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException
import paramiko
import threading
from flask import Flask, render_template, request, redirect, url_for
import serial_script
from pymongo import MongoClient
import subprocess
import time
from pymongo.errors import ConnectionFailure , ServerSelectionTimeoutError
from bson import ObjectId
from device_config import configure_device, configure_network_interface, manage_vlan_on_device, configure_vty_console, configure_spanning_tree, configure_etherchannel
from routing_config import configure_static_route, configure_rip_route, configure_ospf_route, configure_eigrp_route
from concurrent.futures import ThreadPoolExecutor


app = Flask(__name__, template_folder='templates')
app.secret_key = 'Supawitadmin123_'

# client = MongoClient('mongodb://10.0.0.3:27017/')
client = MongoClient('mongodb+srv://admin:Supawitadmin123_@cluster0.ikx1g.mongodb.net/device_management?retryWrites=true&w=majority')
db = client['device_management']  # กำหนดชื่อฐานข้อมูล
device_collection = db['devices']  # กำหนดชื่อคอลเล็กชัน

########## MongoDB Status ###################################
def check_mongo_connection():
    try:
        client.admin.command('ping')
        return 'connected'
    except (ConnectionFailure, ServerSelectionTimeoutError):
        return 'disconnected'
@app.route('/mongo_status')
def mongo_status():
    status = check_mongo_connection()
    return jsonify({"status": status})


########## login Page #######################################
@app.route('/')
def login_frist():
    return render_template('login.html')
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    if username == 'admin' and password == 'admin':
        return redirect(url_for('initialization'))
    else:
        return '<script>alert("Incorrect username or password!!"); window.location.href="/";</script>'
@app.route('/logout', methods=['POST'])
def logout():
    return render_template('login.html')

########## Device Initialization ###########################
@app.route('/initialization_page', methods=['GET'])
def initialization_page():
    return render_template('initialization.html')
@app.route('/initialization', methods=['GET', 'POST'])
def initialization():
    if request.method == 'POST':
        consoleport = request.form.get('consoleport')
        hostname = request.form.get('hostname')
        domainname = request.form.get('domainname')
        privilege_password = request.form.get('privilegepassword')
        ssh_username = request.form.get('ssh_username')
        ssh_password = request.form.get('ssh_password')
        interface = request.form.get('interface')
        interface_type = request.form.get('interfaceType')
        ip_address = request.form.get('ip_address')
        save_startup = request.form.get('save_startup')

        if interface_type == "DHCP":
            ip_address = "dhcp"
        else:
            if not ip_address:
                flash("Please provide an IP address for Manual configuration.", 'danger')
                return render_template('initialization.html')
        try:
            if ip_address != "dhcp":
                if "/" in ip_address:
                    ip_address_split = ip_address.split('/')[0]
               
                device_data = {
                    "name": hostname, 
                    "device_info": {
                        "device_type": "cisco_ios",
                        "ip": ip_address_split,
                        "username": ssh_username,
                        "password": ssh_password,
                        "secret": privilege_password,
                        "session_log": "output.log"
                    }
                }

                existing_device_hostname = device_collection.find_one({"name": hostname})
                if existing_device_hostname:
                    flash("This hostname is already in use. Please choose a different hostname.", "danger")
                    return render_template('initialization.html', hostname_duplicate="This hostname is already in use. Please enter a different hostname.")

                existing_device = device_collection.find_one({"device_info.ip": ip_address_split})
                if existing_device:
                    return render_template('initialization.html', ip_duplicate= "This IP address is already in use. Please enter a different IP address.")
                
                device_collection.insert_one(device_data)

                # call serial ####
                serial_script.commands(consoleport, hostname, domainname, privilege_password,
                                   ssh_username, ssh_password, interface, ip_address, save_startup)
            else:
                serial_script.commands(consoleport, hostname, domainname, privilege_password,
                                   ssh_username, ssh_password, interface, ip_address, save_startup)
            return render_template('initialization.html', success="Device successfully initialized!")
            
        except Exception as e:
            return render_template('initialization.html', error=f"An error occurred: {e}")

    return render_template('initialization.html')


########## Device Record Management ########################
@app.route('/record_mnmg_page', methods=['GET'])
def record_mnmg_page():
    return render_template('record_mnmg.html')
@app.route('/record_mnmg', methods=['GET', 'POST'])
def record_mnmg_form():
    if request.method == 'POST':
        name = request.form.get('name')
        ip_address = request.form.get('ip_address')
        privilege_password = request.form.get('privilegepassword')
        ssh_username = request.form.get('ssh_username')
        ssh_password = request.form.get('ssh_password')
        device_data = {
            "name": name,
            "device_info": {
                "device_type": "cisco_ios",
                "ip": ip_address,
                "username": ssh_username,
                "password": ssh_password,
                "secret": privilege_password,
                "session_log": "output.log"
            }
        }

        existing_device_hostname = device_collection.find_one({"name": name})
        if existing_device_hostname:
            flash("This hostname is already in use. Please choose a different hostname.", "danger")
            return redirect(url_for('record_mnmg_page'))

        existing_device = device_collection.find_one({"device_info.ip": ip_address})
        if existing_device:
            flash("This IP address is already in use. Please enter a different IP address.", "danger")
            return redirect(url_for('record_mnmg_page'))

        device_collection.insert_one(device_data)
        flash("Device record added successfully!", "success")
        return redirect(url_for('record_mnmg_page'))

    return render_template('record_mnmg.html')


########## Devices Informaion ##############################
@app.route('/devices_informaion_page', methods=['GET'])
def devices_information():
    try:
        cisco_devices = list(device_collection.find())
    except ServerSelectionTimeoutError:
        cisco_devices = None  
    return render_template('devices_information.html', cisco_devices=cisco_devices)
@app.route('/delete', methods=['POST'])
def delete_device():
    ip_address = request.form.get('ip_address')
    device_collection.delete_one({"device_info.ip": ip_address}) 
    return redirect(url_for('devices_information')) 
@app.route('/edit/<ip_address>', methods=['GET'])
def edit_device(ip_address):
    try:
        device = device_collection.find_one({"device_info.ip": ip_address})
        if device:
            return render_template('edit_device.html', device=device)
        else:
            return "Device not found", 404
    except Exception as e:
        return str(e)
@app.route('/update', methods=['POST'])
def update_device():
    current_ip = request.form.get('current_ip')
    new_ip = request.form.get('new_ip')  # ค่าของ IP ใหม่ที่ได้รับจากฟอร์ม
    name = request.form.get('name')
    username = request.form.get('username')
    password = request.form.get('password')
    secret = request.form.get('secret')

    try:
        existing_device_hostname = device_collection.find_one({"name": name, "device_info.ip": {"$ne": current_ip}})
        if existing_device_hostname:
            device = device_collection.find_one({"device_info.ip": current_ip})
            return render_template('edit_device.html', alert_message="This hostname is already in use. Please choose a different hostname.", device=device)

        # ตรวจสอบว่า IP ซ้ำหรือไม่ (เฉพาะเมื่อ IP มีการเปลี่ยนแปลง)
        if current_ip != new_ip:
            existing_device = device_collection.find_one({"device_info.ip": new_ip})
            if existing_device:
                # หาก IP ซ้ำ แจ้งเตือนและส่งกลับไปยังหน้า edit
                device = device_collection.find_one({"device_info.ip": current_ip})
                return render_template('edit_device.html', alert_message="This IP address is already in use. Please enter a different IP address.", device=device)

            device_collection.delete_one({"device_info.ip": current_ip})

            # เพิ่มข้อมูลใหม่พร้อม IP Address ใหม่
            device_collection.insert_one({
                "name": name,
                "device_info": {
                    "device_type": "cisco_ios",
                    "ip": new_ip,
                    "username": username,
                    "password": password,
                    "secret": secret,
                    "session_log": "output.log"
                }
            })
        else:
            device_collection.update_one(
                {"device_info.ip": current_ip},
                {"$set": {
                    "name": name,
                    "device_info.username": username,
                    "device_info.password": password,
                    "device_info.secret": secret
                }}
            )
        
        return redirect(url_for('devices_information'))
    
    except Exception as e:
        device = device_collection.find_one({"device_info.ip": current_ip})
        return render_template('edit_device.html', alert_message=f"An error occurred: {str(e)}", device=device)

@app.route('/ping', methods=['POST'])
def ping_device():
    ip_address = request.get_json().get('ip_address')
    
    if ip_address is None:
        return jsonify({"success": False, "message": "IP address is required."})

    print(f"Ping to: {ip_address}")
    try:
        result = subprocess.run(['ping', '-n', '3', ip_address], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            output = f"Ping to {ip_address} successful.\n{result.stdout}"
            return jsonify({"success": True, "message": output})
        else:
            output = f"Ping to {ip_address} failed.\n{result.stderr}"
            return jsonify({"success": False, "message": output})
    except Exception as e:
        error_message = f"An error occurred while pinging the device: {str(e)}"
        return jsonify({"success": False, "message": error_message})


########## Basic Settings ##################################
@app.route('/basic_settings_page', methods=['GET'])
def basic_settings_page():
    try:
        cisco_devices = list(device_collection.find())
    except ServerSelectionTimeoutError:
        cisco_devices = None  
    return render_template('basic_settings.html', cisco_devices=cisco_devices)

@app.route('/basic_settings', methods=['GET', 'POST'])
def basic_settings():
    try:
        cisco_devices = list(device_collection.find())
    except ServerSelectionTimeoutError:
        cisco_devices = None  

    if request.method == 'POST':
        device_name = request.form.get('device_name')  
        hostname = request.form.get('hostname')
        secret_password = request.form.get('secret_password')
        banner = request.form.get('banner')
        many_hostname = request.form.get('many_hostname')
        
        device_ips = []
        device_names_processed = set()

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
                        return f'<script>alert("Duplicate IP detected for device {name} with IP {ip_address}"); window.location.href="/basic_settings";</script>'

                if not found_any:
                    print(f"Device {name} not found in database")
                    return f'<script>alert("Device {name} not found in database"); window.location.href="/basic_settings";</script>'
                
                device_names_processed.add(name)

        elif device_name:
            device = device_collection.find_one({"device_info.ip": device_name})
            if device:
                device_ips.append(device["device_info"]["ip"])
            else:
                print(f"Device with IP {device_name} not found in database")
                return f'<script>alert("Device with IP {device_name} not found in database"); window.location.href="/basic_settings";</script>'

        threads = []
        print("Device IPs to configure:", device_ips)
        
        for ip in device_ips:
            device = device_collection.find_one({"device_info.ip": ip})
            
            if device:
                thread = threading.Thread(target=configure_device, args=(device, hostname, secret_password, banner, device_collection))
                threads.append(thread)
                thread.start()
            else:
                print(f"Device with IP {ip} not found in database")
                return f'<script>alert("Device with IP {ip} not found in database"); window.location.href="/basic_settings";</script>'
        
        for thread in threads:
            thread.join()

        return redirect(url_for('basic_settings_page'))

    return render_template('basic_settings.html', cisco_devices=cisco_devices)


########## Network Interface Settings ######################
@app.route('/network_interface_page', methods=['GET'])
def network_interface_page():
    try:
        cisco_devices = list(device_collection.find())
    except ServerSelectionTimeoutError:
        cisco_devices = None  
    return render_template('network_interface_config.html', cisco_devices=cisco_devices)
@app.route('/network_interface_settings', methods=['GET', 'POST'])
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
        ip_address_ipv6 = request.form.get('ip_address_ipv6')
        enable_ipv6 = request.form.get('enable_ipv6') == 'on'
        disable_ipv6 = request.form.get('disable_ipv6') == 'on'
        delete_ipv6 = request.form.get('delete_ipv6') == 'on'

        interfaces_du = request.form.get('interfaces_du')
        speed_duplex = request.form.get('speed_duplex')
        
        device_ips = []
        device_names_processed = set()

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
                        return f'<script>alert("Duplicate IP detected for device {name} with IP {ip_address}"); window.location.href="/network_interface_page";</script>'

                if not found_any:
                    print(f"Device {name} not found in database")
                    return f'<script>alert("Device {name} not found in database"); window.location.href="/network_interface_page";</script>'
                
                device_names_processed.add(name)

        elif device_name:
            device = device_collection.find_one({"device_info.ip": device_name})
            if device:
                device_ips.append(device["device_info"]["ip"])
            else:
                print(f"Device with IP {device_name} not found in database")
                return f'<script>alert("Device with IP {device_name} not found in database"); window.location.href="/network_interface_page";</script>'

        threads = []
        print("Device IPs to configure:", device_ips)
        
        
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
                print(f"Device with IP {ip} not found in database")
                return f'<script>alert("Device with IP {ip} not found in database"); window.location.href="/network_interface_page";</script>'
        
        for thread in threads:
            thread.join()

        return redirect(url_for('network_interface_page'))

    return render_template('network_interface_config.html', cisco_devices=cisco_devices)


########## VLAN Management Settings ########################
@app.route('/vlan_settings_page', methods=['GET'])
def vlan_settings_page():
    try:
        cisco_devices = list(device_collection.find())
    except ServerSelectionTimeoutError:
        cisco_devices = None  
    return render_template('vlan_management.html', cisco_devices=cisco_devices)
@app.route('/vlan_settings', methods=['GET', 'POST'])
def vlan_settings():
    try:
        cisco_devices = list(device_collection.find())
    except ServerSelectionTimeoutError:
        cisco_devices = None

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
                        vlan_range_enable.extend(range(int(start_vlan), int(end_vlan) + 1))  # ขยายช่วง VLAN
                    except ValueError:
                        return f'<script>alert("Invalid VLAN range for Enable: {entry}"); window.location.href="/vlan_settings";</script>'
                else:  # ถ้าไม่ใช่ช่วงให้เพิ่มแค่ VLAN ที่ระบุ
                    try:
                        vlan_range_enable.append(int(entry))
                    except ValueError:
                        return f'<script>alert("Invalid VLAN ID for Enable: {entry}"); window.location.href="/vlan_settings";</script>'

        vlan_range_disable = []
        if disable_vlans and vlan_id_disable:
            vlan_entries_disable = vlan_id_disable.split(',')
            for entry in vlan_entries_disable:
                entry = entry.strip()
                if '-' in entry:  # ตรวจสอบว่ามีการใช้ช่วงหรือไม่
                    try:
                        start_vlan, end_vlan = entry.split('-')
                        vlan_range_disable.extend(range(int(start_vlan), int(end_vlan) + 1))  # ขยายช่วง VLAN
                    except ValueError:
                        return f'<script>alert("Invalid VLAN range for Disable: {entry}"); window.location.href="/vlan_settings";</script>'
                else:  # ถ้าไม่ใช่ช่วงให้เพิ่มแค่ VLAN ที่ระบุ
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
        for ip in device_ips:
            device = device_collection.find_one({"device_info.ip": ip})
            if device:
                # thread = threading.Thread(target=manage_vlan_on_device, args=(device, vlan_range, vlan_range_del, vlan_changes, vlan_range_enable, vlan_range_disable))
                thread = threading.Thread(target=manage_vlan_on_device, args=(
                    device, vlan_range, vlan_range_del, vlan_changes, vlan_range_enable, vlan_range_disable, 
                    access_vlans, access_interface, access_vlan_id, disable_dtp, 
                    trunk_ports, trunk_mode_select, trunk_interface, trunk_native,
                    allow_vlan
                ))
                threads.append(thread)
                thread.start()

        for thread in threads:
            thread.join()

        return redirect(url_for('vlan_settings_page'))

    return render_template('vlan_management.html', cisco_devices=cisco_devices)


########## Management Settings #############################
@app.route('/management_settings_page', methods=['GET'])
def management_settings_page():
    try:
        cisco_devices = list(device_collection.find())
    except ServerSelectionTimeoutError:
        cisco_devices = None  
    return render_template('management_settings.html', cisco_devices=cisco_devices)
@app.route('/management_settings', methods=['POST'])
def management_settings():
    device_name = request.form.get("device_name")
    many_hostname = request.form.get("many_hostname")
    password_vty = request.form.get("password_vty")
    authen_method = request.form.get("authen_method_select")
    exec_timeout_vty = request.form.get("exec_timeout_vty")
    login_method = request.form.get("login_method_select")
    logging_sync_vty = request.form.get("logging_sync_vty") == "on"

    password_console = request.form.get("password_console")
    exec_timeout_console = request.form.get("exec_timeout_console")
    logging_sync_console = request.form.get("logging_sync_con") == "on"
    authen_method_con = request.form.get("authen_method_console_select")

    pool_name = request.form.get("pool_name")
    network = request.form.get("network")
    dhcp_subnet = request.form.get("dhcp_subnet")
    dhcp_exclude = request.form.get("dhcp_exclude")
    default_router = request.form.get("default_router")
    dns_server = request.form.get("dns_server")
    domain_name = request.form.get("domain_name")

    ntp_server = request.form.get("ntp_server")
    time_zone_name = request.form.get("time_zone_name")
    hour_offset = request.form.get("hour_offset")

    snmp_ro = request.form.get("snmp_ro")
    snmp_rw = request.form.get("snmp_rw")
    snmp_contact = request.form.get("snmp_contact")
    snmp_location = request.form.get("snmp_location")

    enable_cdp = request.form.get("enable_cdp") == "on"
    disable_cdp = request.form.get("disable_cdp") == "on"
    enable_lldp = request.form.get("enable_lldp") == "on"
    disable_lldp = request.form.get("disable_lldp") == "on"

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
                target=configure_vty_console,
                args=(device, password_vty, authen_method, exec_timeout_vty, login_method, logging_sync_vty, 
                    password_console, exec_timeout_console, logging_sync_console, authen_method_con,
                    pool_name, network, dhcp_subnet, dhcp_exclude, default_router, dns_server, domain_name,
                    ntp_server, time_zone_name, hour_offset, snmp_ro, snmp_rw, snmp_contact, snmp_location,
                    enable_cdp, disable_cdp, enable_lldp, disable_lldp))
            threads.append(thread)
            thread.start()

    for thread in threads:
        thread.join()

    return redirect(url_for('management_settings_page'))

########## Spanning Tree Protocol ###########################
@app.route('/stp_page', methods=['GET'])
def stp_page():
    try:
        cisco_devices = list(device_collection.find())
    except ServerSelectionTimeoutError:
        cisco_devices = None  
    return render_template('stp.html', cisco_devices=cisco_devices)
@app.route('/stp_settings', methods=['POST'])
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
                target=configure_spanning_tree,
                args=(device, stp_mode, root_primary, root_vlan_id, root_secondary, root_secondary_vlan_id,
                      portfast_enable, portfast_disable, portfast_int_enable, portfast_int_disable)
            )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    return redirect(url_for('stp_page'))


########## Aggregation Protocols ###########################
@app.route('/etherchannel', methods=['GET'])
def etherchannel():
    try:
        cisco_devices = list(device_collection.find())
    except ServerSelectionTimeoutError:
        cisco_devices = None  
    return render_template('etherchannel.html', cisco_devices=cisco_devices)
@app.route('/etherchannel_settings', methods=['POST'])
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

    return redirect(url_for('etherchannel'))


########## Static Route ####################################
@app.route('/static_page', methods=['GET'])
def static_page():
    try:
        cisco_devices = list(device_collection.find())
    except ServerSelectionTimeoutError:
        cisco_devices = None  
    return render_template('static.html', cisco_devices=cisco_devices)
@app.route('/static_settings', methods=['POST'])
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

    return redirect(url_for('static_page')) 


########## RIPv2 Route #####################################
@app.route('/rip_page', methods=['GET'])
def rip_page():
    try:
        cisco_devices = list(device_collection.find())
    except ServerSelectionTimeoutError:
        cisco_devices = None  
    return render_template('ripv2.html', cisco_devices=cisco_devices)
@app.route('/rip_settings', methods=['POST'])
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

    return redirect(url_for('rip_page'))


########## OSPF Routing #####################################
@app.route('/ospf_page', methods=['GET'])
def ospf_page():
    try:
        cisco_devices = list(device_collection.find())
    except ServerSelectionTimeoutError:
        cisco_devices = None  
    return render_template('ospf.html', cisco_devices=cisco_devices)
@app.route('/ospf_settings', methods=['POST'])
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
                      remove_destination_networks,remove_ospf_areas, delete_process_id,
                      process_id_input)
            )
            threads.append(thread)
            thread.start()

    for thread in threads:
        thread.join()

    return redirect(url_for('ospf_page'))


########## EIGRP Routing ####################################
@app.route('/eigrp_page', methods=['GET'])
def eigrp_page():
    try:
        cisco_devices = list(device_collection.find())
    except ServerSelectionTimeoutError:
        cisco_devices = None  
    return render_template('eigrp.html', cisco_devices=cisco_devices)
@app.route('/eigrp_settings', methods=['POST'])
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

    return redirect(url_for('eigrp_page'))


########## Erase Configuration #############################
@app.route('/erase_config_page', methods=['GET'])
def erase_config_page():
    try:
        cisco_devices = list(device_collection.find())
    except ServerSelectionTimeoutError:
        cisco_devices = None  
    return render_template('eraseconfig.html', cisco_devices=cisco_devices)

@app.route('/erase', methods=['POST'])
def erase_device():
    cisco_devices = list(device_collection.find())
    try:
        device_index = int(request.form.get('device_index'))
        if 0 <= device_index < len(cisco_devices):
            device = cisco_devices[device_index]
            device_info = device['device_info']

            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            ssh_client.connect(hostname=device_info['ip'], username=device_info['username'], password=device_info['password'])

            shell = ssh_client.invoke_shell()
            time.sleep(1)

            shell.send('enable\n')
            time.sleep(1)
            shell.send(device_info['secret'] + '\n')  # ใช้ enable password ที่ดึงจาก MongoDB
            time.sleep(1)

            shell.send('config terminal\n')
            time.sleep(1)
            shell.send('config-register 0x2102\n')  # ค่าที่ตั้งสำหรับบูต
            time.sleep(1)
            shell.send('exit\n')
            time.sleep(1)

            shell.send('erase startup-config\n')
            time.sleep(1)
            shell.send('\n')  # ตอบยืนยันการลบ
            time.sleep(1)

            shell.send('reload\n')
            time.sleep(1)
            shell.send('no\n')  # ตอบไม่ต้อง reload ทันที
            time.sleep(1)
            shell.send('\n')  # ยืนยัน reload ถามอีกครั้ง
            time.sleep(1)

            output = shell.recv(65535).decode('utf-8')
            print(output)

            ssh_client.close()

            device_collection.delete_one({"device_info.ip": device_info['ip']})

            return '<script>alert("Configuration erased successfully! Device will reload."); window.location.href="/erase_config_page";</script>'

        else:
            return '<script>alert("Device not found!"); window.location.href="/erase_config_page";</script>'

    except Exception as e:
        print(e)
        return '<script>alert("Failed to erase configuration. Please try again."); window.location.href="/erase_config_page";</script>'

@app.route('/reload', methods=['POST'])
def reload_device():
    cisco_devices = list(device_collection.find())
    try:
        device_index = int(request.form.get('device_index'))
        if 0 <= device_index < len(cisco_devices):
            device = cisco_devices[device_index]
            device_info = device['device_info']

            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(hostname=device_info['ip'], username=device_info['username'], password=device_info['password'])

            shell = ssh_client.invoke_shell()
            time.sleep(1)

            shell.send('enable\n')
            time.sleep(1)
            shell.send(device_info['secret'] + '\n')
            time.sleep(1)

            shell.send('reload\n')
            time.sleep(1)
            shell.send('\n')
            time.sleep(1)

            output = shell.recv(65535).decode('utf-8')
            print(output)

            if "telnet" in output or "register" in output:
                shell.send('config terminal\n')
                time.sleep(1)
                shell.send('config-register 0x2102\n')  # ค่าที่ตั้งสำหรับบูต
                time.sleep(1)
                shell.send('exit\n')
                time.sleep(1)

            shell.send('reload\n')
            time.sleep(1)
            shell.send('\n')
            time.sleep(1)

            output = shell.recv(65535).decode('utf-8')
            print(output)

            if "Save?" in output or "modified." in output:
                return '''
                <div id="loader" style="display:none;"></div>
                <div id="confirmModal" style="display:none;">
                    <div class="modal-content">
                        <p>System configuration has been modified. Save?</p>
                        <button id="yesButton" style="background-color: #2e4ead; color: white; padding: 10px; border: none; border-radius: 5px; cursor: pointer;">Yes</button>
                        <button id="noButton" style="background-color: tomato; color: white; padding: 10px; border: none; border-radius: 5px; cursor: pointer;">No</button>
                    </div>
                </div>
                <script>
                    function showLoader() {
                        document.getElementById('loader').style.display = 'block'; // แสดง loader
                    }

                    function hideLoader() {
                        document.getElementById('loader').style.display = 'none'; // ซ่อน loader
                    }

                    function showConfirmModal() {
                        document.getElementById('confirmModal').style.display = 'flex'; // แสดง modal
                    }

                    document.getElementById('yesButton').addEventListener('click', function() {
                        handleResponse("yes");
                    });

                    document.getElementById('noButton').addEventListener('click', function() {
                        handleResponse("no");
                    });

                    function handleResponse(response) {
                        showLoader(); // แสดง loader เมื่อผู้ใช้คลิก
                        fetch("/handle_save_response", {
                            method: "POST",
                            headers: { "Content-Type": "application/x-www-form-urlencoded" },
                            body: "device_index=" + encodeURIComponent("''' + str(device_index) + '''") + "&save_response=" + encodeURIComponent(response)
                        }).then(() => {
                            alert("Configuration response has been sent.");
                            hideLoader(); // ซ่อน loader หลังจากส่งข้อมูลเสร็จ
                            window.location.href = "/erase_config_page";
                        }).catch(() => {
                            alert("Failed to send response. Please try again.");
                            hideLoader(); // ซ่อน loader หากมีข้อผิดพลาด
                        });

                        hideModal(); // ซ่อน modal หลังจากเลือกแล้ว
                    }

                    function hideModal() {
                        document.getElementById('confirmModal').style.display = 'none'; // ซ่อน modal
                    }

                    // แสดง modal เมื่อโหลดหน้า
                    window.onload = function() {
                        showConfirmModal();
                    };
                </script>
                <style>
                    * {
                    font-family: 'Roboto', sans-serif;
                    }
                    #confirmModal {
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background-color: rgba(0, 0, 0, 0.5);
                        display: flex;
                        justify-content: center;
                        align-items: center;
                    }

                    .modal-content {
                        background-color: white;
                        padding: 20px;
                        border-radius: 5px;
                        text-align: center;
                    }

                    /* Loader Styles */
                    #loader {
                        display: none;
                        position: fixed; /* ใช้ fixed เพื่อให้ loader ติดอยู่ที่ตำแหน่ง */
                        top: 50%; /* วางอยู่ที่ 50% ของความสูง */
                        left: 50%; /* วางอยู่ที่ 50% ของความกว้าง */
                        transform: translate(-50%, -50%); /* ปรับตำแหน่งให้แน่ใจว่ามันอยู่กลาง */
                        z-index: 9999;
                        border: 8px solid rgba(255, 255, 255, 0.2);
                        border-top: 8px solid #3498db;
                        border-radius: 50%;
                        width: 5vw;
                        height: 5vw;
                        max-width: 80px;
                        max-height: 80px;
                        animation: spin 1.5s linear infinite;
                        box-shadow: 0 0 15px rgba(0, 0, 0, 0.3);
                    }

                    @keyframes spin {
                    0% {
                        transform: rotate(0deg);
                    }

                    100% {
                        transform: rotate(360deg);
                        }
                    }
                </style>
            '''
            else:
                ssh_client.close()
                return '<script>alert("Device will reload without saving."); window.location.href="/erase_config_page";</script>'
        
        else:
            return '<script>alert("Device not found!"); window.location.href="/erase_config_page";</>'
    
    except Exception as e:
        print(e)
        return '<script>alert("Failed to reload device. Please try again."); window.location.href="/erase_config_page";</script>', 500

@app.route('/handle_save_response', methods=['POST'])
def handle_save_response():
    cisco_devices = list(device_collection.find())
    try:
        device_index = int(request.form.get('device_index'))
        save_response = request.form.get('save_response')
        
        if 0 <= device_index < len(cisco_devices):
            device = cisco_devices[device_index]
            device_info = device['device_info']

            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(hostname=device_info['ip'], username=device_info['username'], password=device_info['password'])

            shell = ssh_client.invoke_shell()
            time.sleep(1)

            shell.send('enable\n')
            time.sleep(1)
            shell.send(device_info['secret'] + '\n')
            time.sleep(1)

            shell.send('reload\n')
            time.sleep(1)

            shell.send(save_response + '\n')  # ส่ง "yes" หรือ "no" ไปยังอุปกรณ์
            time.sleep(1)
            shell.send('\n')
            time.sleep(1)

            output = shell.recv(65535).decode('utf-8')
            print(output)
            ssh_client.close()
            return '<script>alert("Response sent to device."); window.location.href="/erase_config_page";</script>'
        else:
            return '<script>alert("Device not found!"); window.location.href="/erase_config_page";</script>'
    except Exception as e:
        print(e)
        return '<script>alert("Failed to handle save response. Please try again."); window.location.href="/erase_config_page";</script>', 500



########## Show Configuration ##############################
@app.route('/show_config_page', methods=['GET'])
def show_config_page():
    try:
        cisco_devices = list(device_collection.find())
    except ServerSelectionTimeoutError:
        cisco_devices = []  
    return render_template('showconfig.html', cisco_devices=cisco_devices)
@app.route('/show-config', methods=['POST', 'GET'])
def show_config():
    cisco_devices = list(device_collection.find())
    if request.method == 'POST':
        device_name = request.form.get('device_name')
        selected_commands = request.form.getlist('selected_commands')

        print("Device Name:", device_name)
        print("Selected Commands:", selected_commands)

        device = device_collection.find_one({"name": device_name})

        if device:
            device_info = device['device_info']
            try:
                config_data = ""

                device_info = {
                    "device_type": "cisco_ios",  # ประเภทของอุปกรณ์ Cisco
                    "host": device_info['ip'],  # IP ของอุปกรณ์
                    "username": device_info['username'],  # ชื่อผู้ใช้
                    "password": device_info['password'],  # รหัสผ่าน
                    "secret": device_info['secret'],  # รหัสผ่าน Enable
                    "timeout": 10  # ตั้งเวลา timeout
                }

                net_connect = ConnectHandler(**device_info)
                net_connect.enable()  

                commands_to_execute = {
                    "show_running_config": 'show running-config',
                    "show_version": 'show version',
                    "show_interfaces": 'show interfaces',
                    "show_ip_interface_brief": 'show ip interface brief',
                    "show_ip_route": 'show ip route',
                    "show_vlan": 'show vlan',
                    "show_cdp_neighbors": 'show cdp neighbors',
                    "show_ip_protocols": 'show ip protocols',
                    "show_mac_address_table": 'show mac address-table dynamic',
                    "show_clock": 'show clock',
                    "show_logging": 'show logging',
                    "show_interfaces_trunk": 'show interfaces trunk',
                    "show_etherch_sum": 'show etherch sum'
                }

                for command in selected_commands:
                    if command in commands_to_execute:
                        output = net_connect.send_command(commands_to_execute[command])
                        config_data += f"<span style='color: #2e4ead; font-size: 1.2em; font-weight: bold;'>{command.replace('_', ' ')}</span> \n" + output + "\n"

                net_connect.disconnect()
                print(config_data)
                return render_template('showconfig.html', cisco_devices=cisco_devices, config_data=config_data)

            except Exception as e:
                print(e)
                error_message = "ไม่สามารถดึงข้อมูลการกำหนดค่าได้ กรุณาลองใหม่อีกครั้ง"
                return render_template('showconfig.html', cisco_devices=cisco_devices, error_message=error_message)

    return render_template('showconfig.html', cisco_devices=cisco_devices)



########## Device Details SNMP #############################
@app.route('/devices_details_page', methods=['GET'])
def device_detials_page():
    try:
        cisco_devices = list(device_collection.find())
    except ServerSelectionTimeoutError:
        cisco_devices = []  
    return render_template('device_details_snmp.html', cisco_devices=cisco_devices)
@app.route('/get_snmp', methods=['POST'])
def device_details_form():
    device_ip = request.form.get("device_name") #get ip
    device_info_record = device_collection.find_one({"device_info.ip": device_ip})
    device_info = device_info_record['device_info']
    real_switch = False
    
    try:
        net_connect = ConnectHandler(**device_info)
        net_connect.enable()
        show_version_output = net_connect.send_command("show version")
        if "switch" in show_version_output.lower():
            real_switch = True
        net_connect.disconnect()
    except Exception as e:
        print(f"Error during SSH connection or command execution: {e}")
        show_version_output = "Error fetching show version"

    # check switch
    if real_switch:
        result = subprocess.run(["node", "static/port_real.js", device_ip], capture_output=True, text=True)
        output = result.stdout if result.returncode == 0 else "Error fetching ports"
    else:
        result = subprocess.run(["node", "static/port_virtual_device.js", device_ip], capture_output=True, text=True)
        output = result.stdout if result.returncode == 0 else "Error fetching ports"

    uptime_result = subprocess.run(["node", "static/uptime.js", device_ip], capture_output=True, text=True)
    uptime_output = uptime_result.stdout if uptime_result.returncode == 0 else "Error fetching uptime"
    location_result = subprocess.run(["node", "static/location.js", device_ip], capture_output=True, text=True)
    location_output = location_result.stdout if location_result.returncode == 0 else "Error fetching location"
    contact_result = subprocess.run(["node", "static/contact.js", device_ip], capture_output=True, text=True)
    contact_output = contact_result.stdout if contact_result.returncode == 0 else "Error fetching contact"
    description_result = subprocess.run(["node", "static/description.js", device_ip], capture_output=True, text=True)
    description_output = description_result.stdout if description_result.returncode == 0 else "Error fetching system description"
    sysname_result = subprocess.run(["node", "static/sysname.js", device_ip], capture_output=True, text=True)
    sysname_output = sysname_result.stdout if sysname_result.returncode == 0 else "Error fetching sysName"
    cisco_devices = list(device_collection.find())
    return render_template('device_details_snmp.html', cisco_devices=cisco_devices, output=output, 
                           uptime=uptime_output,location=location_output,contact=contact_output,
                           description=description_output,sysname=sysname_output)



