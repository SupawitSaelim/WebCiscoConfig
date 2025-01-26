# detect_ports.py
import json
from serial.tools import list_ports
import os

def detect_serial_ports():
    ports = list_ports.comports()
    port_list = []
    
    for port in ports:
        port_list.append({
            'device': port.device,
            'description': port.description,
            'hwid': port.hwid
        })
    
    with open('detected_ports.json', 'w') as f:
        json.dump(port_list, f)

if __name__ == '__main__':
    detect_serial_ports()