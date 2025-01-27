from flask import Blueprint, render_template, request, redirect, url_for, flash
from pymongo.errors import ServerSelectionTimeoutError
import threading
from core.device.device_config import configure_vty_console
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException


management_settings = Blueprint('management_settings', __name__)

def init_management_settings(device_collection):
    @management_settings.route('/management_settings_page', methods=['GET'])
    def management_settings_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = None
            flash("Database connection error. Please try again later.", "danger")  
        return render_template('management_settings.html', cisco_devices=cisco_devices)

    @management_settings.route('/management_settings', methods=['POST'])
    def management_settings_route():
        try:
            device_name = request.form.get("device_name")
            many_hostname = request.form.get("many_hostname")
            password_vty = request.form.get("password_vty")
            authen_method = request.form.get("authen_method_select")
            exec_timeout_vty = request.form.get("exec_timeout_vty")
            login_method = request.form.get("login_method_select")
            logging_sync_vty = request.form.get("logging_sync_vty") == "on"

            password_console = request.form.get("password_console")
            exec_timeout_console = request.form.get("exec_timeout_console")
            logging_sync_console = request.form.get("logging_sync_con") == "on"
            authen_method_con = request.form.get("authen_method_console_select")

            pool_name = request.form.get("pool_name")
            network = request.form.get("network")
            dhcp_subnet = request.form.get("dhcp_subnet")
            dhcp_exclude = request.form.get("dhcp_exclude")
            default_router = request.form.get("default_router")
            dns_server = request.form.get("dns_server")
            domain_name = request.form.get("domain_name")
            pool_name_del = request.form.get("pool_name_del")

            ntp_server = request.form.get("ntp_server")
            time_zone_name = request.form.get("time_zone_name")
            hour_offset = request.form.get("hour_offset")

            snmp_ro = request.form.get("snmp_ro")
            snmp_rw = request.form.get("snmp_rw")
            snmp_contact = request.form.get("snmp_contact")
            snmp_location = request.form.get("snmp_location")

            enable_cdp = request.form.get("enable_cdp") == "on"
            disable_cdp = request.form.get("disable_cdp") == "on"
            enable_lldp = request.form.get("enable_lldp") == "on"
            disable_lldp = request.form.get("disable_lldp") == "on"

            device_ips = []

            if device_name:
                device = device_collection.find_one({"device_info.ip": device_name})
                if device:
                    device_ips.append(device["device_info"]["ip"])
                else:
                    return f'<script>alert("Device with IP {device_name} not found in database"); window.location.href="/management_settings_page";</script>'

            if many_hostname:
                for host in many_hostname.split(','):
                    device = device_collection.find_one({"name": host.strip()})
                    if device:
                        device_ips.append(device["device_info"]["ip"])
                    else:
                        return f'<script>alert("Device {host} not found in database"); window.location.href="/management_settings_page";</script>'

            threads = []
            results = []
            
            for ip in device_ips:
                device = device_collection.find_one({"device_info.ip": ip})
                if device:
                    result = {'ip': ip}  # Initialize a dictionary to track status and errors
                    results.append(result)
                    thread = threading.Thread(
                        target=configure_vty_console_with_status,
                        args=(device, password_vty, authen_method, exec_timeout_vty, login_method, logging_sync_vty, 
                            password_console, exec_timeout_console, logging_sync_console, authen_method_con,
                            pool_name, network, dhcp_subnet, dhcp_exclude, default_router, dns_server, domain_name, pool_name_del,
                            ntp_server, time_zone_name, hour_offset, snmp_ro, snmp_rw, snmp_contact, snmp_location,
                            enable_cdp, disable_cdp, enable_lldp, disable_lldp),
                        kwargs={'result': result}
                    )
                    threads.append(thread)
                    thread.start()


            for thread in threads:
                thread.join()

            success_devices = []
            failed_devices = []
            
            for result in results:
                if result['status'] == 'success':
                    success_devices.append(result['ip'])
                else:
                    failed_devices.append(f"{result['ip']}: {result['error']}")

            if success_devices:
                flash(f"Configuration successful for devices: {', '.join(success_devices)}", "success")
            
            if failed_devices:
                for device in failed_devices:
                    flash(f"Configuration failed for {device}", "danger")

        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "danger")

        return redirect(url_for('management_settings.management_settings_page'))

    return management_settings

def configure_vty_console_with_status(device, *args, result=None):
    """Wrapper function for configure_vty_console that handles status updates."""
    try:
        configure_vty_console(device, *args)
        if result is not None:
            result['status'] = 'success'
    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        error_message = str(e)
        if "TCP connection to device failed" in error_message:
            error_message = ("TCP connection to device failed. Common causes: "
                             "1. Incorrect hostname or IP address. "
                             "2. Wrong TCP port. "
                             "3. Intermediate firewall blocking access.")
        if result is not None:
            result['status'] = 'failed'
            result['error'] = error_message
    except Exception as e:
        error_message = str(e)
        if "Pattern not detected:" in error_message:  
            error_message = "Unable to access privileged mode (#). Please ensure your enable password or secret password is correct."
        result['status'] = 'failed'
        result['error'] = error_message

