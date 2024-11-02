from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os
from netmiko import ConnectHandler
import paramiko
import threading
from flask import Flask, render_template, request, redirect, url_for
import asyncio
import serial_script
from pymongo import MongoClient
import os
import subprocess

app = Flask(__name__, template_folder='templates')
app.secret_key = 'Supawitadmin123_'

client = MongoClient('mongodb://172.16.99.5:27017/')
db = client['device_management']  # กำหนดชื่อฐานข้อมูล
device_collection = db['devices']  # กำหนดชื่อคอลเล็กชัน

port_status = {}
port_oids = {}
target_ip = ''


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
        # Retrieve values from the form
        consoleport = request.form.get('consoleport')
        hostname = request.form.get('hostname')
        domainname = request.form.get('domainname')
        privilege_password = request.form.get('privilegepassword')
        ssh_username = request.form.get('ssh_username')
        ssh_password = request.form.get('ssh_password')
        interface = request.form.get('interface')
        interface_type = request.form.get('interfaceType')
        ip_address = request.form.get('ip_address')
        subnet_mask = request.form.get('subnet_mask')

        if interface_type == "DHCP":
            ip_address = "dhcp"
        else:
            if not ip_address:
                flash("Please provide an IP address for Manual configuration.", 'danger')
                return render_template('initialization.html')
        try:
            serial_script.commands(consoleport, hostname, domainname, privilege_password,
                                   ssh_username, ssh_password, interface, ip_address, subnet_mask)
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
    cisco_devices = list(device_collection.find())
    return render_template('devices_information.html', cisco_devices=cisco_devices)
@app.route('/delete', methods=['POST'])
def delete_device():
    ip_address = request.form.get('ip_address')
    device_collection.delete_one({"device_info.ip": ip_address}) 
    return redirect(url_for('devices_information')) 


########## Device Details SNMP #############################
@app.route('/devices_details_page', methods=['GET'])
def device_detials_page():
    cisco_devices = list(device_collection.find())
    return render_template('device_details_snmp.html', cisco_devices=cisco_devices)
@app.route('/get_snmp', methods=['POST'])
def device_details_form():
    device_ip = request.form.get("device_name")
    result = subprocess.run(["node", "static/snmp.js", device_ip], capture_output=True, text=True)
    output = result.stdout if result.returncode == 0 else "Error fetching ports"
    uptime_result = subprocess.run(["node", "static/uptime.js", device_ip], capture_output=True, text=True)
    uptime_output = uptime_result.stdout if uptime_result.returncode == 0 else "Error fetching uptime"
    location_result = subprocess.run(["node", "static/location.js", device_ip], capture_output=True, text=True)
    location_output = location_result.stdout if location_result.returncode == 0 else "Error fetching location"
    contact_result = subprocess.run(["node", "static/contact.js", device_ip], capture_output=True, text=True)
    contact_output = contact_result.stdout if contact_result.returncode == 0 else "Error fetching contact"
    description_result = subprocess.run(["node", "static/description.js", device_ip], capture_output=True, text=True)
    description_output = description_result.stdout if description_result.returncode == 0 else "Error fetching system description"
    cisco_devices = list(device_collection.find())
    return render_template('device_details_snmp.html', cisco_devices=cisco_devices, output=output, uptime=uptime_output,location=location_output,contact=contact_output,description=description_output)