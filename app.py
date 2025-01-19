# Flask imports
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

# Configuration imports
from config.settings import SECRET_KEY
from config.mongodb import init_mongodb_connection

# Core components
from core.ssh.ssh_manager import SSHManager
from core.security.security_checker import SecurityChecker
from core.scheduler.tasks import init_scheduler, cleanup_ssh_sessions

# Route imports - Device
from routes.device.initialization import init_device_initialization_routes
from routes.device.record import init_device_record_routes
from routes.device.details import init_device_details_routes
from routes.device.info import init_device_info_routes
from routes.device.search import init_device_search_routes

# Route imports - Network
from routes.network.interface import init_network_interface
from routes.network.vlan import init_vlan_settings
from routes.network.stp import init_stp_routes

# Route imports - Management
from routes.management.basic_settings import init_basic_settings
from routes.management.settings import init_management_settings
from routes.management.aggregation import init_aggregation_routes
from routes.management.erase_config import init_erase_config_routes

# Route imports - Routing
from routes.routing.static import init_static_routes
from routes.routing.rip import init_rip_routes
from routes.routing.ospf import init_ospf_routes
from routes.routing.eigrp import init_eigrp_routes

# Route imports - Security & System
from routes.security.check import init_security_check_routes
from routes.system.show_config import init_show_config_routes
from routes.ssh.ssh import init_ssh_routes
from routes.system.status import init_system_status_routes

# Utility imports
from dotenv import load_dotenv
import os

# Initialize Flask app
app = Flask(__name__, template_folder='templates')
app.secret_key = SECRET_KEY
socketio = SocketIO(app)

# Load environment variables
load_dotenv()

# Initialize MongoDB connection
db, device_collection = init_mongodb_connection()

# Initialize core components
ssh_manager = SSHManager(max_sessions=50)
security_checker = SecurityChecker(
    device_collection=device_collection,
    model_path='models/ml/lr_model.pkl',
    timezone='Asia/Bangkok'
)

def register_blueprints():
    """Register all blueprints with the app"""
    
    # SSH routes need special handling due to socketio
    init_ssh_routes(app, socketio, ssh_manager)
    
    # Device routes
    app.register_blueprint(init_device_initialization_routes(device_collection))
    app.register_blueprint(init_device_record_routes(device_collection))
    app.register_blueprint(init_device_details_routes(device_collection))
    app.register_blueprint(init_device_info_routes(device_collection))
    app.register_blueprint(init_device_search_routes(device_collection))
    
    # Network routes
    app.register_blueprint(init_network_interface(device_collection))
    app.register_blueprint(init_vlan_settings(device_collection))
    app.register_blueprint(init_stp_routes(device_collection))
    
    # Management routes
    app.register_blueprint(init_basic_settings(device_collection))
    app.register_blueprint(init_management_settings(device_collection))
    app.register_blueprint(init_aggregation_routes(device_collection))
    app.register_blueprint(init_erase_config_routes(device_collection))
    
    # Routing routes
    app.register_blueprint(init_static_routes(device_collection))
    app.register_blueprint(init_rip_routes(device_collection))
    app.register_blueprint(init_ospf_routes(device_collection))
    app.register_blueprint(init_eigrp_routes(device_collection))
    
    # Security and System routes
    app.register_blueprint(init_security_check_routes(device_collection))
    app.register_blueprint(init_show_config_routes(device_collection))
    app.register_blueprint(init_system_status_routes(db))

@app.route('/')
def login_first():
    """Render login page"""
    return render_template('initialization.html')

if __name__ == "__main__":
    # Register all blueprints
    register_blueprints()
    
    # Initialize scheduler
    scheduler = init_scheduler(security_checker, ssh_manager)
    
    # Run the app
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)