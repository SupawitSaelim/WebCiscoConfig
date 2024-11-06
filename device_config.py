from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException
from pymongo import MongoClient
from bson import ObjectId

def configure_device(device, hostname, secret_password, banner, device_collection):
    device_info = device["device_info"]
    
    try:
        net_connect = ConnectHandler(**device_info)
        net_connect.enable()

        if hostname:
            output = net_connect.send_config_set([f'hostname {hostname}'])
            print(f"Hostname output for {device['name']}:", output)
            device_collection.update_one({"_id": ObjectId(device["_id"])}, {"$set": {"name": hostname}})
            net_connect.set_base_prompt()
        
        if secret_password:
            output = net_connect.send_config_set([f'enable secret {secret_password}'])
            device_collection.update_one({"_id": ObjectId(device["_id"])}, {"$set": {"device_info.secret": secret_password}})
            print(f"Enable secret output for {device['name']}:", output)
        
        if banner:
            output = net_connect.send_config_set([f'banner motd # {banner} #'])
            print(f"Banner output for {device['name']}:", output)
        
        net_connect.disconnect()
    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        print(f"Error connecting to {device['name']}: {e}")
        return f'<script>alert("Error connecting to {device["name"]}: {str(e)}"); window.location.href="/basic_settings";</script>'
