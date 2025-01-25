# device_info_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from datetime import timedelta
import subprocess
import platform

def init_device_info_routes(device_collection):
    device_info_blueprint = Blueprint('device_info', __name__)
    
    @device_info_blueprint.route('/devices_informaion_page', methods=['GET'])
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

    @device_info_blueprint.route('/search_devices', methods=['GET'])
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

        results = list(device_collection.find(query).sort("timestamp", -1).limit(50))

        for device in results:
            if "_id" in device:
                device["_id"] = str(device["_id"])
            if "timestamp" in device:
                utc_time = device["timestamp"]
                device["timestamp"] = (utc_time + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')

        return jsonify(results)

    @device_info_blueprint.route('/delete', methods=['POST'])
    def delete_device(): 
        ip_address = request.form.get('ip_address')
        device_collection.delete_one({"device_info.ip": ip_address})
        return redirect(url_for('device_info.devices_information'))

    @device_info_blueprint.route('/edit/<ip_address>', methods=['GET'])
    def edit_device(ip_address):
        try:
            device = device_collection.find_one({"device_info.ip": ip_address})
            if device:
                return render_template('edit_device.html', device=device)
            else:
                return "Device not found", 404
        except Exception as e:
            return str(e)

    @device_info_blueprint.route('/update', methods=['POST'])
    def update_device():
        current_ip = request.form.get('current_ip')
        new_ip = request.form.get('new_ip')
        name = request.form.get('name')
        username = request.form.get('username')
        password = request.form.get('password')
        secret = request.form.get('secret')

        try:
            existing_device_hostname = device_collection.find_one(
                {"name": name, "device_info.ip": {"$ne": current_ip}}
            )
            if existing_device_hostname:
                device = device_collection.find_one({"device_info.ip": current_ip})
                return render_template(
                    'edit_device.html',
                    alert_message="This hostname is already in use. Please choose a different hostname.",
                    device=device
                )

            current_device = device_collection.find_one({"device_info.ip": current_ip})
            if not current_device:
                return "Device not found", 404

            timestamp = current_device.get('timestamp', None)

            if current_ip != new_ip:
                existing_device = device_collection.find_one({"device_info.ip": new_ip})
                if existing_device:
                    device = device_collection.find_one({"device_info.ip": current_ip})
                    return render_template(
                        'edit_device.html',
                        alert_message="This IP address is already in use. Please enter a different IP address.",
                        device=device
                    )

                device_collection.delete_one({"device_info.ip": current_ip})
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
                    "timestamp": timestamp
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
            
            return redirect(url_for('device_info.devices_information'))
        
        except Exception as e:
            device = device_collection.find_one({"device_info.ip": current_ip})
            return render_template('edit_device.html', alert_message=f"An error occurred: {str(e)}", device=device)

    @device_info_blueprint.route('/ping', methods=['POST'])
    def ping_device():
        ip_address = request.get_json().get('ip_address')
        
        if ip_address is None:
            return jsonify({"success": False, "message": "IP address is required."})
        
        system = platform.system().lower()

        try:
            if system == "windows":
                command = ['ping', '-n', '3', ip_address]
            elif system in ["linux", "darwin"]:  # Linux and macOS
                command = ['ping', '-c', '3', ip_address]
            else:
                return jsonify({"success": False, "message": f"Unsupported operating system: {system}"})

            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if result.returncode == 0:
                output = f"Ping to {ip_address} successful.\n{result.stdout}"
                return jsonify({"success": True, "message": output})
            else:
                output = f"Ping to {ip_address} failed.\n{result.stderr}"
                return jsonify({"success": False, "message": output})
                
        except Exception as e:
            error_message = f"An error occurred while pinging the device: {str(e)}"
            return jsonify({"success": False, "message": error_message})

    return device_info_blueprint