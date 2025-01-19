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
from device_info_routes import init_device_info_routes
from security_checker import SecurityChecker   
from ssh_manager import SSHManager
from erase_config_routes import init_erase_config_routes

# Utility imports
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import pytz
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
device_info_blueprint = init_device_info_routes(device_collection)
app.register_blueprint(device_info_blueprint)
erase_config_blueprint = init_erase_config_routes(device_collection)
app.register_blueprint(erase_config_blueprint)


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


def cleanup_ssh_sessions():
    ssh_manager.cleanup_inactive_sessions()

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

