from flask import Blueprint, render_template, request, flash, redirect
from pymongo.errors import ServerSelectionTimeoutError
import subprocess

device_details_routes = Blueprint('device_details_routes', __name__)

def run_snmp_command(script_path, device_ip, community='public'):
    """Helper function to run SNMP-related scripts and return the output or error."""
    try:
        result = subprocess.run(
            ["node", script_path, device_ip, community],
            capture_output=True, text=True, check=True
        )
        if "Error fetching system description" in result.stdout or not result.stdout.strip():
            return "SNMP not configured or unreachable"
        
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error fetching data from {script_path}: {e}"

def init_device_details_routes(device_collection):
    @device_details_routes.route('/devices_details_page', methods=['GET'])
    def device_detials_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = []  
        return render_template('device_details_snmp.html', cisco_devices=cisco_devices)

    @device_details_routes.route('/get_snmp', methods=['POST'])
    def device_details_form():
        device_ip = request.form.get("device_name")
        community = request.form.get("community", "public")
        device_info_record = device_collection.find_one({"device_info.ip": device_ip})
        
        if not device_info_record:
            return f"Device with IP {device_ip} not found", 404
        
        sw_l3, sw_l2, device_type = False, False, ''
        
        description_output = run_snmp_command("static/snmp/description.js", device_ip,community)
        if "SNMP not configured or unreachable" in description_output:
            flash("Error: SNMP not configured or unreachable. Please configure SNMP on the device or Community string is correct", "error")
            return redirect('/devices_details_page')

        if "switch" in description_output.lower() and "L3" in description_output:
            device_type = "Switch Layer3"
            sw_l3 = True
        elif "switch" in description_output.lower() or "C2" in description_output:
            device_type = "Switch Layer2"
            sw_l2 = True
        else:
            device_type = "Router"
        
        # Get port details based on device type
        if sw_l3:
            output = run_snmp_command("static/snmp/port_l3.js", device_ip, community)
        elif sw_l2:
            output = run_snmp_command("static/snmp/port_l2.js", device_ip, community)
        else:
            output = run_snmp_command("static/snmp/port_router.js", device_ip, community)

        # Fetch other SNMP details
        uptime_output = run_snmp_command("static/snmp/uptime.js", device_ip, community)
        location_output = run_snmp_command("static/snmp/location.js", device_ip,community)
        contact_output = run_snmp_command("static/snmp/contact.js", device_ip,community)
        description_output = run_snmp_command("static/snmp/description.js", device_ip,community)
        sysname_output = run_snmp_command("static/snmp/sysname.js", device_ip,community)
        
        cisco_devices = list(device_collection.find())
        
        return render_template(
            'device_details_snmp.html',
            cisco_devices=cisco_devices,
            selected_ip=device_ip,
            output=output,
            uptime=uptime_output,
            location=location_output,
            contact=contact_output,
            description=description_output,
            sysname=sysname_output,
            device_type=device_type
        )

    return device_details_routes
