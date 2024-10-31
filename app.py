from flask import Flask, render_template, request, redirect, url_for, flash   
import json
import os
from netmiko import ConnectHandler
import paramiko
import threading
from flask import Flask, render_template, request, redirect, url_for
import asyncio
import serial_script

app = Flask(__name__, template_folder='templates')

app.secret_key = 'Supawitadmin123_'

# json_file_path = 'cisco_device.json'
# cisco_devices = []

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


########## Device Initialization ###########################
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
            serial_script.commands(consoleport, hostname, domainname, privilege_password, ssh_username, ssh_password, interface, ip_address,subnet_mask)
            return render_template('initialization.html', success="Device successfully initialized!") 
        except Exception as e:
            return render_template('initialization.html', error=f"An error occurred: {e}")

    return render_template('initialization.html')
