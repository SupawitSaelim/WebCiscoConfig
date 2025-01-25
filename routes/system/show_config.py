from flask import Blueprint, render_template, request, redirect, url_for, flash
from pymongo.errors import ServerSelectionTimeoutError
from netmiko import ConnectHandler
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException
from datetime import datetime
from pytz import timezone
th_tz = timezone('Asia/Bangkok')

show_config_routes = Blueprint('show_config_routes', __name__)

def init_show_config_routes(device_collection):
    @show_config_routes.route('/show_config_page', methods=['GET'])
    def show_config_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = []
            flash("Database connection error. Please try again later.", "danger")
        return render_template('showconfig.html', cisco_devices=cisco_devices)

    @show_config_routes.route('/show-config', methods=['POST', 'GET'])
    def show_config():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            flash("Database connection error. Please try again later.", "danger")
            return redirect(url_for('show_config_routes.show_config_page'))

        if request.method == 'POST':
            device_name = request.form.get('device_name')
            selected_commands = request.form.getlist('selected_commands')  

            device = device_collection.find_one({"name": device_name})

            if not device:
                flash(f"Device '{device_name}' not found in the database.", "danger")
                return redirect(url_for('show_config_routes.show_config_page'))

            device_info = device.get('device_info', {})
            if not all(key in device_info for key in ['ip', 'username', 'password', 'secret']):
                flash(f"Device '{device_name}' has incomplete connection details.", "danger")
                return redirect(url_for('show_config_routes.show_config_page'))

            if device:
                device_info = device['device_info']
                try:
                    device_info = {
                        "device_type": "cisco_ios",  
                        "host": device_info['ip'],  
                        "username": device_info['username'],  
                        "password": device_info['password'],  
                        "secret": device_info['secret'],  
                        "timeout": 10  # ตั้งเวลา timeout
                    }

                    net_connect = ConnectHandler(**device_info)
                    net_connect.enable()  

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
                        "show_interfaces_trunk": 'show interfaces trunk',
                        "show_etherch_sum": 'show etherch sum',
                        "show_lldp_neighbors": 'show lldp neighbors',
                        "show_startup": 'show startup-config',
                        "show_interfaces_status": 'show int status',
                        "show_ipv6_interface_brief": 'show ipv6 int br',
                        "show_flash": 'show flash:',
                        "show_dhcp_pool": 'show ip dhcp pool',
                        "show_dhcp_bind": 'show ip dhcp binding',
                        "show_ntp_status": 'show ntp status',
                        "show_spanning_tree": 'show spanning-tree',
                        "show_spanning_tree_sum": 'show spanning-tree sum',
                        "show_environment": 'show environment',
                        "show_inventory": 'show inventory',
                        "show_platform": 'show platform',
                        "show_ip_nat_translations": 'show ip nat translations',
                        "show_ip_arp": 'show ip arp',
                        "show_ip_ospf_neighbor": 'show ip ospf neighbor',
                        "show_ip_eigrp_neighbor": 'show ip eigrp neighbor',
                        "show_bgp_summary": 'show bgp summary',
                        "show_ip_rip_database": 'show ip rip database',
                        "show_vrf": 'show vrf',
                        "show_processes_cpu": 'show processes cpu',
                        "show_ip_sla_statistics": 'show ip sla statistics',
                        "show_cdp": 'show cdp',
                        "show_lldp": 'show lldp',
                        "show_interfaces_switchport": 'show int sw'
                    }

                    config_data = ""
                    for command in selected_commands:
                        if command in commands_to_execute:
                            output = net_connect.send_command(commands_to_execute[command])
                            config_data += f"<span style='color: #2e4ead; font-size: 1.2em; font-weight: bold;'>{command.replace('_', ' ')}</span> \n" + output + "\n"
                            config_data = f"Generated at: {datetime.now(th_tz).strftime('%Y-%m-%d %H:%M:%S')} (UTC+7)\n\n" + config_data

                    net_connect.disconnect()

                    return render_template('showconfig.html', cisco_devices=cisco_devices, config_data=config_data, selected_device=device_name)
                
                except NetMikoTimeoutException:
                    flash(f"Connection timed out while trying to reach {device_info['host']}. Please check if the device is reachable and SSH is enabled.", "danger")
                    return redirect(url_for('show_config_routes.show_config_page'))
                except NetMikoAuthenticationException:
                    flash(f"Authentication failed for device {device_info['host']}. Please verify the username and password.", "danger")
                    return redirect(url_for('show_config_routes.show_config_page'))
                except Exception as e:
                    flash(f"An unexpected error occurred: {str(e)}", "danger")
                    return redirect(url_for('show_config_routes.show_config_page'))

        return render_template('showconfig.html', cisco_devices=cisco_devices)

    return show_config_routes