from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import timedelta
import paramiko
import time
from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException
import socket

def init_erase_config_routes(device_collection):
    erase_config_blueprint = Blueprint('erase_config', __name__)

    @erase_config_blueprint.route('/erase_config_page', methods=['GET'])
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

    @erase_config_blueprint.route('/erase', methods=['POST'])
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
                output = shell.recv(65535).decode('utf-8')
                shell.send(device_info['secret'] + '\n')
                time.sleep(1)
                output += shell.recv(65535).decode('utf-8')

                shell.send('config terminal\n')
                time.sleep(1)
                output += shell.recv(65535).decode('utf-8')

                if output.count("Password:") >= 3:
                    ssh_client.close()
                    return '<script>alert("Authentication failed: Incorrect enable password"); window.location.href="/erase_config_page";</script>'
                
                shell.send('config-register 0x2102\n')
                time.sleep(1)
                output += shell.recv(65535).decode('utf-8')
                print(output)
                shell.send('exit\n')
                time.sleep(1)
                
                shell.send('erase startup-config\n')
                time.sleep(1)
                shell.send('\n')
                time.sleep(1)

                shell.send('reload\n')
                time.sleep(1)
                shell.send('no\n')
                time.sleep(1)
                shell.send('\n')
                time.sleep(1)

                shell.settimeout(30)  
                try:
                    output = shell.recv(65535).decode('utf-8')
                except socket.timeout:
                    ssh_client.close()
                    return '<script>alert("Command timeout: Device not responding"); window.location.href="/erase_config_page";</script>'
                if "unless the configuration" in output:
                    ssh_client.close()
                    return '''<script>
                        alert("Reload to the ROM monitor only allowed from console line unless the configuration register boot bits are non-zero.");
                        window.location.href="/erase_config_page";
                    </script>'''
                

                ssh_client.close()
                device_collection.delete_one({"device_info.ip": device_info['ip']})
                return '<script>alert("Configuration erased successfully! Device will reload."); window.location.href="/erase_config_page";</script>'
            else:
                return '<script>alert("Device not found!"); window.location.href="/erase_config_page";</script>'
        except Exception as e:
            print(f"Error: {e}")
            if ssh_client:
                ssh_client.close()
            return '<script>alert("Failed to erase configuration. Please try again."); window.location.href="/erase_config_page";</script>'

    @erase_config_blueprint.route('/reload', methods=['POST'])
    def reload_device():
        cisco_devices = list(device_collection.find())
        try:
            ip_address = request.form.get('ip_address')
            device = next((device for device in cisco_devices if device['device_info']['ip'] == ip_address), None)
            
            if device:
                device_info = device['device_info']
                print('reloading to: ', device['device_info']['ip'])
                
                try:
                    ssh_client = paramiko.SSHClient()
                    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh_client.connect(hostname=device_info['ip'], 
                                    username=device_info['username'], 
                                    password=device_info['password'])

                    shell = ssh_client.invoke_shell()
                    time.sleep(1)

                    shell.send('enable\n')
                    time.sleep(1)
                    shell.send(device_info['secret'] + '\n')
                    time.sleep(1)

                    # Check if config-register needs to be set
                    shell.send('show version | include Configuration register\n')
                    time.sleep(2)
                    output = shell.recv(65535).decode('utf-8')
                    
                    if "0x2102" not in output:
                        shell.send('config terminal\n')
                        time.sleep(1)
                        shell.send('config-register 0x2102\n')
                        time.sleep(1)
                        shell.send('exit\n')
                        time.sleep(1)

                    # Send reload command
                    shell.send('reload\n')
                    time.sleep(1)
                    
                    # Try to read any pending output
                    try:
                        output = shell.recv(65535).decode('utf-8')
                        if "Save?" in output or "modified" in output:
                            return render_template('confirm_modal.html', ip_address=ip_address)
                        elif "unless the configuration" in output:
                            ssh_client.close()
                            return '''<script>
                                alert("Reload to the ROM monitor only allowed from console line unless the configuration register boot bits are non-zero.");
                                window.location.href="/erase_config_page";
                            </script>'''
                    except Exception:
                        # Connection might be closed here, which is expected
                        pass
                    
                    try:
                        shell.send('\n')  # Confirm reload
                        time.sleep(1)
                    except Exception:
                        # Connection might be closed here, which is expected
                        pass

                    try:
                        ssh_client.close()
                    except Exception:
                        pass

                    # If we got this far, assume reload was successful
                    return '<script>alert("Device is reloading..."); window.location.href="/erase_config_page";</script>'

                except (paramiko.SSHException, socket.error) as e:
                    # If connection was lost after sending reload command, consider it successful
                    if "Socket is closed" in str(e) or "EOF" in str(e):
                        return '<script>alert("Device is reloading..."); window.location.href="/erase_config_page";</script>'
                    else:
                        raise e

            else:
                return '<script>alert("Device not found!"); window.location.href="/erase_config_page";</script>'
        
        except Exception as e:
            print(f"Reload error: {str(e)}")
            # Check if the error indicates connection loss after reload
            if "Socket is closed" in str(e) or "EOF" in str(e):
                return '<script>alert("Device is reloading..."); window.location.href="/erase_config_page";</script>'
            return '<script>alert("Failed to reload device. Please check the device status."); window.location.href="/erase_config_page";</script>'

    @erase_config_blueprint.route('/handle_save_response', methods=['POST'])
    def handle_save_response():
        cisco_devices = list(device_collection.find())
        try:
            ip_address = request.form.get('ip_address')
            device = next((device for device in cisco_devices if device['device_info']['ip'] == ip_address), None)
            save_response = request.form.get('save_response')
            
            if device:
                device_info = device['device_info']

                try:
                    ssh_client = paramiko.SSHClient()
                    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh_client.connect(
                        hostname=device_info['ip'],
                        username=device_info['username'],
                        password=device_info['password'],
                        timeout=20
                    )

                    shell = ssh_client.invoke_shell()
                    time.sleep(1)

                    # Enable mode
                    shell.send('enable\n')
                    time.sleep(1)
                    shell.send(device_info['secret'] + '\n')
                    time.sleep(1)

                    # Send reload command
                    shell.send('reload\n')
                    time.sleep(1)

                    try:
                        # Handle save configuration prompt
                        output = shell.recv(65535).decode('utf-8')
                        print("Initial output:", output)
                        
                        # Send save response
                        shell.send(save_response + '\n')
                        time.sleep(3)  # Wait longer for save to complete
                        
                        # Try to capture any output after save response
                        try:
                            output = shell.recv(65535).decode('utf-8')
                            print("Save response output:", output)
                        except Exception as e:
                            print("Error reading save response (expected):", str(e))

                        # Confirm reload
                        try:
                            shell.send('\n')
                            time.sleep(1)
                        except Exception as e:
                            print("Error sending reload confirmation (expected):", str(e))

                    except Exception as e:
                        print("Error during save/reload process (might be normal):", str(e))
                        # If we got here after sending commands, assume it's working
                        if "Socket is closed" in str(e) or "EOF" in str(e):
                            return '<script>alert("Device is reloading..."); window.location.href="/erase_config_page";</script>'

                    try:
                        ssh_client.close()
                    except Exception:
                        pass

                    return '<script>alert("Device is reloading..."); window.location.href="/erase_config_page";</script>'

                except (paramiko.SSHException, socket.error) as e:
                    print("SSH/Socket error:", str(e))
                    # If connection was lost after sending reload command, consider it successful
                    if "Socket is closed" in str(e) or "EOF" in str(e):
                        return '<script>alert("Device is reloading..."); window.location.href="/erase_config_page";</script>'
                    raise e

            else:
                return '<script>alert("Device not found!"); window.location.href="/erase_config_page";</script>'

        except Exception as e:
            print(f"Final error handler: {str(e)}")
            # Check if the error indicates connection loss after reload
            if "Socket is closed" in str(e) or "EOF" in str(e) or "Connection reset by peer" in str(e):
                return '<script>alert("Device is reloading..."); window.location.href="/erase_config_page";</script>'
            return '<script>alert("Operation completed, but there might have been an issue. Please check the device status."); window.location.href="/erase_config_page";</script>'

    @erase_config_blueprint.route('/save', methods=['POST'])
    def save_configuration():
        cisco_devices = list(device_collection.find())

        try:
            ip_address = request.form.get("ip_address")
            print(f"Received IP address: {ip_address}")

            if ip_address is None:
                flash("IP address is missing!", "danger")
                return redirect(url_for('erase_config.erase_config_page'))

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

    return erase_config_blueprint