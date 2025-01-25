from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime
import pytz
from pymongo.errors import ServerSelectionTimeoutError, PyMongoError
import re

device_record_bp = Blueprint('device_record', __name__)

def init_device_record_routes(device_collection):
   def validate_inputs(name, ip_address, ssh_username, ssh_password, privilege_password):
       if not all([name, ip_address, ssh_username, ssh_password, privilege_password]):
           return "All fields are required."
           
       # IP address validation
       ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
       if not re.match(ip_pattern, ip_address):
           return "Invalid IP address format."
           
       # Basic length validations
       if len(name) > 63 or len(name) < 1:
           return "Hostname must be between 1 and 63 characters."
           
       return None

   @device_record_bp.route('/record_mnmg_page', methods=['GET'])
   def record_mnmg_page():
       return render_template('record_mnmg.html')

   @device_record_bp.route('/record_mnmg', methods=['GET', 'POST'])
   def record_mnmg_form():
       if request.method == 'POST':
           try:
               name = request.form.get('name')
               ip_address = request.form.get('ip_address')
               privilege_password = request.form.get('privilegepassword')
               ssh_username = request.form.get('ssh_username')
               ssh_password = request.form.get('ssh_password')

               # Validate inputs
               validation_error = validate_inputs(name, ip_address, ssh_username, 
                                               ssh_password, privilege_password)
               if validation_error:
                   flash(validation_error, "danger")
                   return redirect(url_for('device_record.record_mnmg_page'))

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

               # Database operations
               try:
                   # Check for existing hostname
                   if device_collection.find_one({"name": name}):
                       flash("This hostname is already in use.", "danger")
                       return redirect(url_for('device_record.record_mnmg_page'))

                   # Check for existing IP
                   if device_collection.find_one({"device_info.ip": ip_address}):
                       flash("This IP address is already in use.", "danger")
                       return redirect(url_for('device_record.record_mnmg_page'))

                   # Insert new device
                   device_collection.insert_one(device_data)
                   flash("Device record added successfully!", "success")

               except ServerSelectionTimeoutError:
                   flash("Database connection timeout. Please try again.", "danger")
               except PyMongoError as e:
                   flash(f"Database error occurred: {str(e)}", "danger")
               
           except Exception as e:
               flash(f"An unexpected error occurred: {str(e)}", "danger")
           
           return redirect(url_for('device_record.record_mnmg_page'))

       return render_template('record_mnmg.html')

   return device_record_bp