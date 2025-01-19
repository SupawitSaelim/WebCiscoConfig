# security_check_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from auto_sec import automate_sec
import pprint

def init_security_check_routes(device_collection):
    security_check = Blueprint('security_check', __name__)
    
    @security_check.route('/config_checker', methods=['GET'])
    def config_checker():
        try:
            page = int(request.args.get('page', 1))  
            per_page = 10
            skip = (page - 1) * per_page

            cisco_devices = list(device_collection.find().skip(skip).limit(per_page))
            
            total_devices = device_collection.count_documents({})
            total_pages = (total_devices + per_page - 1) // per_page

        except Exception as e:
            cisco_devices = []  
            total_pages = 1
            page = 1

        return render_template('securitychecker.html', 
                             cisco_devices=cisco_devices, 
                             total_pages=total_pages, 
                             current_page=page)

    @security_check.route('/fix_device/<device_ip>', methods=['POST'])
    def fix_device(device_ip):
        device = device_collection.find_one({"device_info.ip": device_ip})
        
        if device:
            device_info = device['device_info']
            
            print("Device info being sent to automate_sec:")
            pprint.pprint(device_info)
            
            result = automate_sec(device_info, device_collection.database)
            
            if result:
                flash("Device configured successfully!", "success")
            else:
                flash("Failed to configure device", "danger")
        else:
            flash(f"Device with IP {device_ip} not found.", "danger")

        return redirect(url_for('security_check.config_checker'))

    return security_check