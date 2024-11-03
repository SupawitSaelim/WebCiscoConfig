from flask import Flask, render_template, request, redirect, url_for, flash,jsonify
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
import time

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


########## Erase Configuration #############################
@app.route('/erase_config_page', methods=['GET'])
def erase_config_page():
    cisco_devices = list(device_collection.find())
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
            shell.send('yes\n')  # ตอบยืนยันการลบ
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
def execute_command(shell, command, wait_time=1):
    """ส่งคำสั่งไปยัง shell และรอผลลัพธ์"""
    shell.send(command + '\n')
    time.sleep(wait_time)  # รอเวลาสำหรับการประมวลผลคำสั่ง
    output = shell.recv(65535).decode('utf-8')
    return output

@app.route('/show_config_page', methods=['GET'])
def show_config_page():
    cisco_devices = list(device_collection.find())
    return render_template('showconfig.html', cisco_devices=cisco_devices)

@app.route('/show-config', methods=['POST', 'GET'])
def show_config():
    cisco_devices = list(device_collection.find())
    print(cisco_devices)
    if request.method == 'POST':
        device_name = request.form.get('device_name')
        selected_commands = request.form.getlist('selected_commands')

        print("Device Name:", device_name)
        print("Selected Commands:", selected_commands)

        device = device_collection.find_one({"name": device_name})
        print(device)

        if device:
            device_info = device['device_info']
            try:
                config_data = ""

                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh_client.connect(hostname=device_info['ip'], username=device_info['username'], password=device_info['password'])

                shell = ssh_client.invoke_shell()
                time.sleep(1)

                execute_command(shell, 'enable')
                execute_command(shell, device_info['secret'])  # ใช้ secret แทน enable password

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
                    "show_interfaces_trunk": 'show interfaces trunk'
                }

                for command in selected_commands:
                    if command in commands_to_execute:
                        output = execute_command(shell, commands_to_execute[command])
                        config_data += f"<span style='color: #2e4ead; font-size: 1em; font-weight: bold;'>{command.replace('_', ' ')}</span> \n" + output + "\n"

                ssh_client.close()  # ปิดการเชื่อมต่อ SSH
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



