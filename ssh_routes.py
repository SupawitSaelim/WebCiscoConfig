from flask import render_template, request, redirect, url_for, session, jsonify
from flask_socketio import emit
from ssh_manager import ssh_connect 

def init_ssh_routes(app, socketio, ssh_manager):
    @app.route('/cli')
    def cli():
        hostname = request.args.get('hostname')
        port = request.args.get('port')
        username = request.args.get('username')
        password = request.args.get('password')

        if not (hostname and port and username and password):
            return redirect(url_for('index'))

        # Print received details to the console for demonstration
        print(f"Hostname: {hostname}, Port: {port}, Username: {username}, Password: {password}")

        session['hostname'] = hostname
        session['port'] = port
        session['username'] = username
        session['password'] = password

        return render_template('cli.html')

    @socketio.on('ssh_connect')
    def handle_ssh_connect(data):
        try:
            if ssh_manager.get_active_sessions_count() >= ssh_manager.max_sessions:
                emit('ssh_output', {
                    'data': 'Error: Maximum session limit reached. Please try again later.\n'
                })
                return
                
            hostname = data.get('hostname')
            port = int(data.get('port'))
            username = data.get('username')
            password = data.get('password')
            sid = request.sid
            
            ssh_manager.remove_session(sid)
            socketio.start_background_task(
                ssh_connect, hostname, port, username, password, sid, ssh_manager, socketio
            )
        except Exception as e:
            emit('ssh_output', {'data': f'Connection error: {str(e)}\n'})

    @socketio.on('ssh_command')
    def handle_ssh_command(data):
        sid = request.sid
        command = data['command']
        session = ssh_manager.get_session(sid)
        
        if session:
            try:
                session['channel'].send(command)
                session['last_active'] = time.time()
            except Exception as e:
                emit('ssh_output', {'data': f"Error sending command: {str(e)}"}, to=sid)
                ssh_manager.remove_session(sid)
        else:
            emit('ssh_output', {'data': 'No active SSH session found\n'}, to=sid)

    @socketio.on('disconnect')
    def handle_disconnect():
        sid = request.sid
        ssh_manager.remove_session(sid)

    @app.route('/ssh-stats')
    def ssh_stats():
        stats = ssh_manager.get_session_stats()
        return jsonify(stats)

    return app