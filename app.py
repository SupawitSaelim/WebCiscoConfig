# Flask imports
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_socketio import SocketIO, emit

# Database imports
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from bson import ObjectId

# Network-related imports
from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException
import paramiko
import netifaces

# Custom route blueprints
from device_initialization_routes import init_device_initialization_routes
from device_record_routes import init_device_record_routes
from basic_settings_routes import init_basic_settings
from network_interface_routes import init_network_interface
from ssh_routes import init_ssh_routes
from management_settings_routes import init_management_settings
from vlan_settings_routes import init_vlan_settings
from stp_routes import init_stp_routes
from aggregation_routes import init_aggregation_routes
from static_routes import init_static_routes
from rip_routes import init_rip_routes
from ospf_routes import init_ospf_routes
from eigrp_routes import init_eigrp_routes
from show_config_routes import init_show_config_routes
from security_check_routes import init_security_check_routes
from device_details_routes import init_device_details_routes

from security_checker import SecurityChecker   
from ssh_manager import SSHManager
from auto_sec import automate_sec
import serial_script

# Utility imports
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import pytz
import subprocess
import time
import os
from dotenv import load_dotenv

# Initialize Flask app
app = Flask(__name__, template_folder='templates')
app.secret_key = 'Supawitadmin123_'
socketio = SocketIO(app)

# Load environment variables and setup MongoDB
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set!")

client = MongoClient(MONGO_URI)
db = client['device_management']
device_collection = db['devices']

# Initialize timezone and SSH manager
thailand_timezone = pytz.timezone('Asia/Bangkok')
ssh_manager = SSHManager(max_sessions=50)

# Initialize and register blueprints
init_ssh_routes(app, socketio, ssh_manager)
basic_settings_blueprint = init_basic_settings(device_collection)
app.register_blueprint(basic_settings_blueprint)
network_interface_blueprint = init_network_interface(device_collection)
app.register_blueprint(network_interface_blueprint)
management_settings_blueprint = init_management_settings(device_collection)
app.register_blueprint(management_settings_blueprint)
vlan_settings_blueprint = init_vlan_settings(device_collection)
app.register_blueprint(vlan_settings_blueprint)
stp_blueprint = init_stp_routes(device_collection)
app.register_blueprint(stp_blueprint)
aggregation_blueprint = init_aggregation_routes(device_collection)
app.register_blueprint(aggregation_blueprint)
static_blueprint = init_static_routes(device_collection)
app.register_blueprint(static_blueprint)
rip_blueprint = init_rip_routes(device_collection)
app.register_blueprint(rip_blueprint)
ospf_blueprint = init_ospf_routes(device_collection)
app.register_blueprint(ospf_blueprint)
eigrp_blueprint = init_eigrp_routes(device_collection)
app.register_blueprint(eigrp_blueprint)
show_config_blueprint = init_show_config_routes(device_collection)
app.register_blueprint(show_config_blueprint)
device_details_blueprint = init_device_details_routes(device_collection)
app.register_blueprint(device_details_blueprint)
device_record_blueprint = init_device_record_routes(device_collection)
app.register_blueprint(device_record_blueprint)
device_init_blueprint = init_device_initialization_routes(device_collection)
app.register_blueprint(device_init_blueprint)
security_check_blueprint = init_security_check_routes(device_collection)
app.register_blueprint(security_check_blueprint)

security_checker = SecurityChecker(
    device_collection=device_collection,
    model_path='lr_model.pkl',
    timezone='Asia/Bangkok'
)

########## init scheduler ###################################
def init_scheduler():
    scheduler = BackgroundScheduler()

    # Add Security Analysis job
    scheduler.add_job(
        security_checker.fetch_and_analyze, 
        'interval', 
        seconds=10, 
        max_instances=2,
        id='security_analysis'
    )
    
    # Add other jobs (e.g., SSH cleanup)
    scheduler.add_job(
        lambda: ssh_manager.cleanup_long_running_sessions(max_session_time=3600),
        'interval',
        hours=1,
        id='long_running_cleanup'
    )

    # Add SSH cleanup job
    scheduler.add_job(
        cleanup_ssh_sessions, 
        'interval', 
        minutes=5,
        id='ssh_cleanup'
    )
    
    scheduler.start()
    return scheduler

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

########## Suggest hostname #################################
''' Search Suggest'''
@app.route('/search_hostname', methods=['GET'])
def search_hostname():
    query = request.args.get('query', '')  # รับคำค้นหาจาก query string
    if query:
        matching_devices = device_collection.find({"name": {"$regex": query, "$options": "i"}})  # ใช้ regex สำหรับค้นหาจากชื่อ
        device_names = [device["name"] for device in matching_devices]
        return jsonify(device_names)  
    return jsonify([])

########## login Page #######################################
@app.route('/')
def login_frist():
    return render_template('initialization.html')


########## Devices Informaion ##############################
@app.route('/devices_informaion_page', methods=['GET'])
def devices_information():
    try:
        page = int(request.args.get('page', 1))
        per_page = 10
        skip = (page - 1) * per_page

        cisco_devices = list(
            device_collection.find().sort("timestamp", -1).skip(skip).limit(per_page)
        )

        for device in cisco_devices:
            if "timestamp" in device:
                utc_time = device["timestamp"]
                local_time = utc_time + timedelta(hours=7)
                device["timestamp"] = local_time

        total_devices = device_collection.count_documents({})
        total_pages = (total_devices + per_page - 1) // per_page

    except Exception as e:
        cisco_devices = None
        total_pages = 1
        page = 1

    return render_template(
        'devices_information.html',
        cisco_devices=cisco_devices,
        total_pages=total_pages,
        current_page=page,
    )
@app.route('/search_devices', methods=['GET'])
def search_devices():
    search_query = request.args.get('search', '')
    query = {}
    if search_query:
        query = {
            "$or": [
                {"name": {"$regex": search_query, "$options": "i"}},
                {"device_info.ip": {"$regex": search_query, "$options": "i"}},
                {"device_info.username": {"$regex": search_query, "$options": "i"}},
            ]
        }

    results = list(device_collection.find(query).sort("timestamp", -1).limit(50))  # จำกัดจำนวนผลลัพธ์

    for device in results:
        if "_id" in device:
            device["_id"] = str(device["_id"])  # แปลง ObjectId เป็น string
        if "timestamp" in device:
            utc_time = device["timestamp"]
            device["timestamp"] = (utc_time + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')

    return jsonify(results)
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

        # ค้นหาอุปกรณ์ปัจจุบัน
        current_device = device_collection.find_one({"device_info.ip": current_ip})
        if not current_device:
            return "Device not found", 404

        # ดึง timestamp ของอุปกรณ์ปัจจุบัน
        timestamp = current_device.get('timestamp', None)

        # ตรวจสอบว่า IP ซ้ำหรือไม่ (เฉพาะเมื่อ IP มีการเปลี่ยนแปลง)
        if current_ip != new_ip:
            existing_device = device_collection.find_one({"device_info.ip": new_ip})
            if existing_device:
                # หาก IP ซ้ำ แจ้งเตือนและส่งกลับไปยังหน้า edit
                device = device_collection.find_one({"device_info.ip": current_ip})
                return render_template('edit_device.html', alert_message="This IP address is already in use. Please enter a different IP address.", device=device)

            # ลบอุปกรณ์ปัจจุบัน
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
                },
                "timestamp": timestamp  # คงค่า timestamp เดิม
            })
        else:
            # อัปเดตข้อมูลโดยไม่เปลี่ยน IP
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
    stats = ssh_manager.get_session_stats()
    return jsonify(stats)
def cleanup_ssh_sessions():
    ssh_manager.cleanup_inactive_sessions()


########## Erase Configuration #############################
@app.route('/erase_config_page', methods=['GET'])
def erase_config_page():
    try:
        page = int(request.args.get('page', 1))
        per_page = 10
        skip = (page - 1) * per_page

        search_query = request.args.get('search', '')
        query = {}
        if search_query:
            query = {
                "$or": [
                    {"name": {"$regex": search_query, "$options": "i"}},
                    {"device_info.ip": {"$regex": search_query, "$options": "i"}},
                    {"device_info.username": {"$regex": search_query, "$options": "i"}},
                ]
            }

        cisco_devices = list(device_collection.find(query).sort("timestamp", -1).skip(skip).limit(per_page))

        for device in cisco_devices:
            if "timestamp" in device:
                utc_time = device["timestamp"]
                local_time = utc_time + timedelta(hours=7)
                device["timestamp"] = local_time

        total_devices = device_collection.count_documents(query)
        total_pages = (total_devices + per_page - 1) // per_page if total_devices > 0 else 1

        return render_template('eraseconfig.html', cisco_devices=cisco_devices, total_pages=total_pages, current_page=page)

    except Exception as e:
        return render_template('eraseconfig.html', cisco_devices=None, total_pages=1, current_page=1)
@app.route('/erase', methods=['POST'])
def erase_device():
    cisco_devices = list(device_collection.find())
    try:
        ip_address = request.form.get('ip_address')
        if not ip_address:
            return "IP address is required!", 400  
        device = next((device for device in cisco_devices if device['device_info']['ip'] == ip_address), None)
        
        if device:
            device_info = device['device_info']
            print('Erasing configuration for', device['device_info']['ip'])

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
        ip_address = request.form.get('ip_address')  
        device = next((device for device in cisco_devices if device['device_info']['ip'] == ip_address), None)
        
        if device:
            device_info = device['device_info']
            print('reloading to: ', device['device_info']['ip'])
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
                return render_template('confirm_modal.html', ip_address=ip_address)
            else:
                ssh_client.close()
                return '<script>alert("Device will reload without saving."); window.location.href="/erase_config_page";</script>'
        else:
            return '<script>alert("Device not found!"); window.location.href="/erase_config_page";</script>'
    
    except Exception as e:
        print(e)
        return '<script>alert("Failed to reload device. Please try again."); window.location.href="/erase_config_page";</script>', 500
@app.route('/handle_save_response', methods=['POST'])
def handle_save_response():
    cisco_devices = list(device_collection.find())
    try:
        ip_address = request.form.get('ip_address') 
        device = next((device for device in cisco_devices if device['device_info']['ip'] == ip_address), None)
        save_response = request.form.get('save_response')
        
        if device:
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
@app.route('/save', methods=['POST'])
def save_configuration():
    cisco_devices = list(device_collection.find())

    try:
        ip_address = request.form.get("ip_address")  
        print(f"Received IP address: {ip_address}")

        if ip_address is None:
            flash("IP address is missing!", "danger")
            return redirect(url_for('erase_config_page'))

        device = next((device for device in cisco_devices if device["device_info"]["ip"] == ip_address), None)

        if device is not None:
            device_info = device["device_info"]
            print(f"Attempting to save configuration for {device['name']}")

            device_info['timeout'] = 10
            net_connect = ConnectHandler(**device_info)
            net_connect.enable()

            config_command = "write memory"
            output = net_connect.send_command(config_command)
            print(f"Save Configuration for {device['name']}:", output)

            net_connect.disconnect()
            flash(f"Configuration saved for {device['name']} successfully.", "success")
        else:
            flash(f"Device with IP {ip_address} not found!", "danger")
    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        flash(f"Error saving configuration: {e}", "danger")

    total_devices = device_collection.count_documents({})
    per_page = 10
    total_pages = (total_devices + per_page - 1) // per_page
    page = 1  

    return render_template('eraseconfig.html', cisco_devices=cisco_devices, total_pages=total_pages, current_page=page)

if __name__ == "__main__":
    # Initialize scheduler before running the app
    scheduler = init_scheduler()

    # Print available interfaces
    interfaces = netifaces.interfaces()
    for interface in interfaces:
        addresses = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in addresses:  # IPv4
            for address in addresses[netifaces.AF_INET]:
                print(f"Flask web server is running at: http://{address['addr']}:5000")

    # Run the app
    socketio.run(app, host="0.0.0.0", port=8888, debug=True)

