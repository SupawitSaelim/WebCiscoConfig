from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime
import pytz

device_record_bp = Blueprint('device_record', __name__)

def init_device_record_routes(device_collection):
    @device_record_bp.route('/record_mnmg_page', methods=['GET'])
    def record_mnmg_page():
        return render_template('record_mnmg.html')

    @device_record_bp.route('/record_mnmg', methods=['GET', 'POST'])
    def record_mnmg_form():
        if request.method == 'POST':
            name = request.form.get('name')
            ip_address = request.form.get('ip_address')
            privilege_password = request.form.get('privilegepassword')
            ssh_username = request.form.get('ssh_username')
            ssh_password = request.form.get('ssh_password')
            tz_bangkok = pytz.timezone('Asia/Bangkok')
            current_time = datetime.now(tz_bangkok).replace(microsecond=0)
            device_data = {
                "name": name,
                "device_info": {
                    "device_type": "cisco_ios",
                    "ip": ip_address,
                    "username": ssh_username,
                    "password": ssh_password,
                    "secret": privilege_password,
                    "session_log": "output.log"
                },
                "timestamp": current_time
            }

            existing_device_hostname = device_collection.find_one({"name": name})
            if existing_device_hostname:
                flash("This hostname is already in use. Please choose a different hostname.", "danger")
                return redirect(url_for('device_record.record_mnmg_page'))

            existing_device = device_collection.find_one({"device_info.ip": ip_address})
            if existing_device:
                flash("This IP address is already in use. Please enter a different IP address.", "danger")
                return redirect(url_for('device_record.record_mnmg_page'))

            device_collection.insert_one(device_data)
            flash("Device record added successfully!", "success")
            return redirect(url_for('device_record.record_mnmg_page'))

        return render_template('record_mnmg.html')

    return device_record_bp
