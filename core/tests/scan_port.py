from flask import Flask, render_template, jsonify
from serial.tools import list_ports
import serial

app = Flask(__name__, template_folder='../../templates')

@app.route('/')
def index():
   ports = list_ports.comports()
   available_ports = [{
       'device': port.device,
       'description': port.description,
       'manufacturer': port.manufacturer,
       'hwid': port.hwid
   } for port in ports]
   print(app.template_folder)
   return render_template('comport.html', ports=available_ports)

@app.route('/connect/<port>')
def connect_port(port):
   try:
       ser = serial.Serial(port, 9600, timeout=1)
       if ser.is_open:
           return jsonify({'status': 'success', 'message': f'Connected to {port}'})
   except Exception as e:
       return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
   app.run(debug=True)