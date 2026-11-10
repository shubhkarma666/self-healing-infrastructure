from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.route('/alert', methods=['POST'])
def handle_alert():
    data = request.json

    for alert in data.get('alerts', []):
        if alert.get('status') == 'firing':
            if alert.get('labels', {}).get('alertname') == 'NginxDown':
                subprocess.run([
                    '/usr/bin/ansible-playbook',
                    '/home/ubuntu/self-healing/restart-nginx.yml'
                ], check=True)

    return jsonify({"message": "Alert processed"}), 200

app.run(host='127.0.0.1', port=5001)
