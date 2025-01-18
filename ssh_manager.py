from threading import Lock
import paramiko
import time
from flask_socketio import emit
from flask import request

class SSHManager:
    def __init__(self, max_sessions=50):
        self.ssh_sessions = {}
        self.lock = Lock()
        self.max_sessions = max_sessions
        
    def add_session(self, sid, client, channel):
        with self.lock:
            if len(self.ssh_sessions) >= self.max_sessions:
                raise Exception("Maximum session limit reached")
            
            self.ssh_sessions[sid] = {
                'client': client,
                'channel': channel,
                'last_active': time.time(),
                'created_at': time.time()
            }

    def get_active_sessions_count(self):
        with self.lock:
            return len(self.ssh_sessions)

    def cleanup_long_running_sessions(self, max_session_time=3600):  # 1 hour
        with self.lock:
            current_time = time.time()
            long_running_sids = [
                sid for sid, session in self.ssh_sessions.items()
                if current_time - session['created_at'] > max_session_time
            ]
            for sid in long_running_sids:
                self.remove_session(sid)

    def get_session_stats(self):
        with self.lock:
            stats = {
                'active_sessions': len(self.ssh_sessions),
                'max_sessions': self.max_sessions,
                'available_slots': self.max_sessions - len(self.ssh_sessions)
            }
            return stats

    def remove_session(self, sid):
        with self.lock:
            if sid in self.ssh_sessions:
                try:
                    session = self.ssh_sessions[sid]
                    if session['channel']:
                        session['channel'].close()
                    if session['client']:
                        session['client'].close()
                except Exception as e:
                    print(f"Error closing session {sid}: {e}")
                finally:
                    del self.ssh_sessions[sid]

    def get_session(self, sid):
        with self.lock:
            return self.ssh_sessions.get(sid)

    def cleanup_inactive_sessions(self, timeout=300):  # 5 minutes timeout
        with self.lock:
            current_time = time.time()
            inactive_sids = [
                sid for sid, session in self.ssh_sessions.items()
                if current_time - session['last_active'] > timeout
            ]
            for sid in inactive_sids:
                self.remove_session(sid)

def ssh_connect(hostname, port, username, password, sid, ssh_manager, socketio):
    client = None
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname, 
            port=port, 
            username=username, 
            password=password,
            timeout=30,
            auth_timeout=20
        )
        
        ssh_channel = client.invoke_shell()
        ssh_manager.add_session(sid, client, ssh_channel)
        
        while True:
            if ssh_channel.recv_ready():
                data = ssh_channel.recv(1024).decode('utf-8')
                socketio.emit('ssh_output', {'data': data}, to=sid)
                # Update last active timestamp
                ssh_manager.ssh_sessions[sid]['last_active'] = time.time()
                
            # Small delay to prevent CPU spinning
            socketio.sleep(0.1)
            
    except Exception as e:
        socketio.emit('ssh_output', {'data': f"Error: {str(e)}"}, to=sid)
    finally:
        ssh_manager.remove_session(sid)