from flask import Blueprint, render_template, request
from pymongo.errors import ServerSelectionTimeoutError
from netmiko import ConnectHandler

show_config_routes = Blueprint('show_config_routes', __name__)

def init_show_config_routes(device_collection):
    @show_config_routes.route('/show_config_page', methods=['GET'])
    def show_config_page():
        try:
            cisco_devices = list(device_collection.find())
        except ServerSelectionTimeoutError:
            cisco_devices = []  
        return render_template('showconfig.html', cisco_devices=cisco_devices)

    @show_config_routes.route('/show-config', methods=['POST', 'GET'])
    def show_config():
        cisco_devices = list(device_collection.find())

        if request.method == 'POST':
            device_name = request.form.get('device_name')
            selected_commands = request.form.getlist('selected_commands')  # รับคำสั่งที่เลือก

            print("Device Name:", device_name)
            print("Selected Commands:", selected_commands)

            device = device_collection.find_one({"name": device_name})

            if device:
                device_info = device['device_info']
                try:
                    device_info = {
                        "device_type": "cisco_ios",  # ประเภทของอุปกรณ์ Cisco
                        "host": device_info['ip'],  # IP ของอุปกรณ์
                        "username": device_info['username'],  # ชื่อผู้ใช้
                        "password": device_info['password'],  # รหัสผ่าน
                        "secret": device_info['secret'],  # รหัสผ่าน Enable
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

                    net_connect.disconnect()
                    print(config_data)

                    return render_template('showconfig.html', cisco_devices=cisco_devices, config_data=config_data)

                except Exception as e:
                    print(e)
                    error_message = "ไม่สามารถดึงข้อมูลการกำหนดค่าได้ กรุณาลองใหม่อีกครั้ง"
                    return render_template('showconfig.html', cisco_devices=cisco_devices, error_message=error_message)

        return render_template('showconfig.html', cisco_devices=cisco_devices)

    return show_config_routes
