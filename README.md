# Self-Healing Infrastructure with Prometheus, Alertmanager & Ansible

## Website - Evidence/Screenshot
![01-nginx-failure-and-auto-recovery.png](screenshots/01-nginx-failure-and-auto-recovery.png)

![02-ansible-webhook-execution.png](screenshots/02-ansible-webhook-execution.png)

## 1. Project Introduction

### What is this project?

Imagine you have a website running on a server. Suddenly, the web server crashes.

Normally, someone has to:
1. Notice that the website is down.
2. Connect to the server.
3. Find the problem.
4. Restart the service manually.

This takes time and requires human intervention.

In this project, we automate that process.

We build a system that detects when NGINX stops working and automatically restarts it.

This concept is called **Self-Healing Infrastructure**.

### Project Objective

To automatically detect service failures, generate alerts, and recover failed services using Prometheus, Alertmanager, Python, and Ansible.

---

## 2. Technologies Used

| Technology | Purpose |
|---|---|
| AWS EC2 | Hosts our Ubuntu server |
| Ubuntu | Operating system |
| NGINX | Sample web server |
| Node Exporter | Collects server metrics |
| Blackbox Exporter | Checks whether NGINX is reachable |
| Prometheus | Collects and evaluates metrics |
| Alertmanager | Handles Prometheus alerts |
| Python Flask | Receives webhook notifications |
| Ansible | Automatically restarts NGINX |

### How do they work together?

Think of the components like a team:

- Prometheus acts like a monitoring person.
- Alertmanager acts like a notification manager.
- Python acts like a messenger.
- Ansible acts like the recovery engineer.
- NGINX is the service being protected.

---

## 3. AWS EC2 Setup

### What is AWS EC2?

EC2 is a service from Amazon Web Services that provides virtual servers.

Instead of buying a physical computer, we rent a virtual machine in the cloud.

### What we did

1. Opened AWS Console.
2. Navigated to EC2.
3. Launched an Ubuntu instance.
4. Selected the t3.small instance type.
5. Created or selected an SSH key pair.
6. Connected to the instance using SSH.

### Why Ubuntu?

We use Ubuntu because it supports all the tools required for this project.

Once connected, we updated the package list:

```bash
sudo apt update
```

**Explanation:**

- `sudo` runs a command with administrator privileges.
- `apt` is Ubuntu's package manager.
- `update` refreshes the available package information.

---

## 4. Installing NGINX

### What is NGINX?

NGINX is a web server that receives HTTP requests and sends responses to users.

We need a sample service that we can deliberately stop and restart.

### Installation

```bash
sudo apt install nginx -y
```

Start NGINX:

```bash
sudo systemctl start nginx
```

Enable automatic startup after reboot:

```bash
sudo systemctl enable nginx
```

Check its status:

```bash
sudo systemctl status nginx
```

Expected result:

`Active: active (running)`

### What does systemctl do?

`systemctl` manages services in Linux.

For example:

```bash
sudo systemctl stop nginx
```

Stops NGINX.

```bash
sudo systemctl start nginx
```

Starts NGINX.

```bash
sudo systemctl restart nginx
```

Restarts NGINX.

We will use these commands later to simulate and recover a failure.

---

## 5. Installing Node Exporter

### What is Node Exporter?

Node Exporter collects information about the server.

For example:
- CPU usage
- Memory usage
- Disk information
- System uptime

Prometheus cannot automatically understand all Linux server metrics. Node Exporter exposes them in a format Prometheus can collect.

### Installation

```bash
sudo apt install prometheus-node-exporter -y
```

Start and enable it:

```bash
sudo systemctl enable --now prometheus-node-exporter
```

Check its status:

```bash
sudo systemctl status prometheus-node-exporter
```

### Understanding Port 9100

Node Exporter normally exposes its metrics on port 9100.

We can verify this using:

```bash
curl http://localhost:9100/metrics
```

This displays the metrics collected from our server.

---

## 6. Installing Prometheus

### What is Prometheus?

Prometheus is a monitoring and metrics collection system.

It periodically collects information from configured targets and stores that information as time-series data.

For example, it can collect CPU usage every 15 seconds.

### Installation

```bash
sudo apt install prometheus -y
```

Start it:

```bash
sudo systemctl enable --now prometheus
```

Check:

```bash
sudo systemctl status prometheus
```

### Understanding Port 9090

Prometheus provides a web interface and API on port 9090.

We can check whether it is working:

```bash
curl http://localhost:9090
```

---

## 7. Configuring Prometheus

### Why do we need configuration?

Prometheus needs to know:
- Which services to monitor.
- Where those services are running.
- How frequently to collect metrics.

We configure these details in:

`/etc/prometheus/prometheus.yml`

Open the file:

```bash
sudo vi /etc/prometheus/prometheus.yml
```

We configured Node Exporter using:

```yaml
- job_name: 'node-exporter'
  static_configs:
    - targets: ['localhost:9100']
```

### Understanding this configuration

- `job_name`: Gives the monitoring target a name.
- `static_configs`: Defines the targets manually.
- `targets`: Specifies where the metrics are available.

Here, `localhost:9100` means Node Exporter is running on the same server.

### Verify the target

```bash
curl -s http://localhost:9090/api/v1/targets
```

We confirmed that the target health was:

`up`

This means Prometheus successfully collected metrics from Node Exporter.

---

## 8. Installing Blackbox Exporter

### What is Blackbox Exporter?

Node Exporter monitors the server itself.

But we also need to check whether our actual website is responding.

That's where Blackbox Exporter comes in.

It checks services using protocols such as HTTP, HTTPS, DNS, and TCP.

In our project, it checks whether NGINX responds to HTTP requests.

### Installation

```bash
sudo apt install prometheus-blackbox-exporter -y
```

Start it:

```bash
sudo systemctl enable --now prometheus-blackbox-exporter
```

### Understanding Port 9115

Blackbox Exporter normally listens on port 9115.

Prometheus sends it a request to check NGINX.

Blackbox Exporter then reports whether the check succeeded.

The important metric is:

`probe_success`

Its values mean:

- `1` = NGINX is reachable.
- `0` = NGINX is unreachable.

This metric is the foundation of our automatic failure detection.

---

## 9. Configuring NGINX Monitoring

We added a Blackbox Exporter monitoring job to Prometheus.

The configuration uses:

```yaml
- job_name: 'nginx'
  metrics_path: /probe
  params:
    module: [http_2xx]
  static_configs:
    - targets:
      - http://localhost:80
  relabel_configs:
    - source_labels: [__address__]
      target_label: __param_target
    - source_labels: [__param_target]
      target_label: instance
    - target_label: __address__
      replacement: localhost:9115
```

### Understanding the configuration

- `job_name`: Names the monitoring job.
- `metrics_path`: Tells Prometheus to use the Blackbox probe endpoint.
- `targets`: Specifies the NGINX URL.
- `replacement`: Sends the probe request to Blackbox Exporter.

Prometheus is checking NGINX through Blackbox Exporter rather than directly.

We restarted Prometheus after changing its configuration:

```bash
sudo systemctl restart prometheus
```

We verified the result with:

```bash
curl -s 'http://localhost:9090/api/v1/query?query=probe_success'
```

A value of `1` confirmed that NGINX was responding.

---

## 10. Creating Prometheus Alert Rules

### What are alert rules?

Monitoring metrics is useful, but we also want Prometheus to recognize problems automatically.

Alert rules define conditions that should generate alerts.

We created:

`/etc/prometheus/alert-rules.yml`

### NGINX failure alert

```yaml
- alert: NginxDown
  expr: probe_success == 0
  for: 30s
  labels:
    severity: critical
  annotations:
    summary: "NGINX is down"
    description: "NGINX has been unreachable for 30 seconds."
```

### Explanation

- `alert`: Name of the alert.
- `expr`: Condition that Prometheus evaluates.
- `probe_success == 0`: NGINX is unreachable.
- `for: 30s`: The condition must remain true for 30 seconds.
- `severity`: Identifies the alert's importance.
- `annotations`: Provides a human-readable explanation.

### CPU alert

We also configured a CPU alert:

```yaml
- alert: HighCPUUsage
  expr: 100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 90
  for: 1m
  labels:
    severity: warning
  annotations:
    summary: "CPU usage is above 90%"
```

This rule checks whether average CPU usage stays above 90%.

The five-minute window smooths short-term CPU fluctuations.

### Connecting the rules

We added the following to the top level of `prometheus.yml`:

```yaml
rule_files:
  - "/etc/prometheus/alert-rules.yml"
```

We validated the configuration:

```bash
promtool check config /etc/prometheus/prometheus.yml
```

Then restarted Prometheus:

```bash
sudo systemctl restart prometheus
```

We checked the loaded rules:

```bash
curl -s http://localhost:9090/api/v1/rules
```

Both rules loaded successfully.

---

## 11. Installing Alertmanager

### What is Alertmanager?

Prometheus detects problems and creates alerts.

Alertmanager receives those alerts and handles their delivery.

It can send notifications to email, messaging platforms, or webhooks.

In our project, we use a webhook.

### Installation

```bash
sudo apt install prometheus-alertmanager -y
```

Start it:

```bash
sudo systemctl enable --now prometheus-alertmanager
```

Check:

```bash
sudo systemctl status prometheus-alertmanager
```

Alertmanager normally listens on port 9093.

---

## 12. Connecting Prometheus to Alertmanager

Prometheus must know where Alertmanager is running.

We added this to `prometheus.yml`:

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - 'localhost:9093'
```

We validated the configuration and restarted Prometheus.

To verify the connection:

```bash
curl -s http://localhost:9090/api/v1/alertmanagers
```

We confirmed that Alertmanager appeared in the active alert managers list.

---

## 13. Installing Ansible

### What is Ansible?

Ansible is an automation tool.

It allows us to perform administrative tasks through written instructions called playbooks.

Instead of manually restarting NGINX, we can ask Ansible to do it.

### Installation

```bash
sudo apt update
sudo apt install ansible -y
```

Check the version:

```bash
ansible --version
```

Test local connectivity:

```bash
ansible localhost -m ping -c local
```

Expected result:

`"ping": "pong"`

This confirms that Ansible can communicate with our local server.

---

## 14. Creating the Ansible Playbook

We created a project directory:

```bash
mkdir -p ~/self-healing
cd ~/self-healing
```

Created:

`restart-nginx.yml`

Our playbook:

```yaml
---
- name: Self-heal NGINX
  hosts: localhost
  connection: local
  become: true

  tasks:
    - name: Restart NGINX
      ansible.builtin.service:
        name: nginx
        state: restarted

    - name: Verify NGINX is running
      ansible.builtin.service:
        name: nginx
        state: started
```

### Understanding the playbook

- `hosts: localhost`: Runs on our EC2 server.
- `connection: local`: No remote SSH connection is required.
- `become: true`: Uses administrator privileges.
- `tasks`: Contains the actions Ansible must perform.
- `state: restarted`: Restarts NGINX.
- `state: started`: Ensures NGINX is running.

### Testing the playbook

```bash
sudo ansible-playbook restart-nginx.yml
```

We confirmed that the playbook completed without failures.

This was important because we needed to verify that Ansible could recover NGINX before connecting it to Alertmanager.

---

## 15. Creating the Python Webhook

### Why do we need a webhook?

Alertmanager can send an HTTP notification, but it does not directly execute our Ansible playbook.

We need a small service that receives the notification and triggers Ansible.

We built that service using Python Flask.

### Installing Flask

```bash
sudo apt install python3-flask -y
```

Created:

`webhook.py`

Our webhook:

```python
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
```

### Understanding the code

**Flask application**

```python
app = Flask(__name__)
```

Creates our small web application.

**Webhook endpoint**

```python
@app.route('/alert', methods=['POST'])
```

Creates an endpoint that accepts POST requests.

**Receiving alerts**

```python
data = request.json
```

Reads the alert information sent by Alertmanager.

**Checking alert status**

```python
if alert.get('status') == 'firing':
```

Ensures that we process active alerts.

**Checking the alert name**

```python
if alert.get('labels', {}).get('alertname') == 'NginxDown':
```

Ensures that only the NGINX failure alert triggers recovery.

**Executing Ansible**

```python
subprocess.run([...], check=True)
```

Runs our Ansible playbook.

The playbook then restarts NGINX.

### Starting the webhook

```bash
sudo python3 /home/ubuntu/self-healing/webhook.py
```

The webhook listens on localhost port 5001.

We kept this process running during our demonstration.

---

## 16. Configuring Alertmanager Webhook

We configured:

`/etc/prometheus/alertmanager.yml`

Configuration:

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: 'self-healing-webhook'
  group_wait: 5s
  group_interval: 30s
  repeat_interval: 1h

receivers:
  - name: 'self-healing-webhook'
    webhook_configs:
      - url: 'http://localhost:5001/alert'
        send_resolved: false
```

### Understanding the configuration

- `route`: Defines how alerts are routed.
- `receiver`: Selects the notification destination.
- `group_wait`: Waits before sending the initial notification.
- `group_interval`: Controls notification timing for updated groups.
- `repeat_interval`: Controls repeated notifications.
- `webhook_configs`: Configures the webhook destination.
- `url`: Points to our Python application.
- `send_resolved: false`: Sends firing notifications, but not recovery notifications.

We validated the configuration:

```bash
sudo amtool check-config /etc/prometheus/alertmanager.yml
```

Then restarted Alertmanager:

```bash
sudo systemctl restart prometheus-alertmanager
```

At this point, the complete automation chain was connected.

---

## 17. Understanding the Complete Architecture

Here is the complete workflow:

```text
             NGINX
               |
               |
        Blackbox Exporter
               |
               |
           Prometheus
               |
          Alert Rules
               |
               |
          Alertmanager
               |
               |
         Python Webhook
               |
               |
            Ansible
               |
               |
         Restart NGINX
               |
               |
        NGINX Running
```

### What happens when NGINX fails?

1. NGINX stops responding.
2. Blackbox Exporter detects the failed HTTP check.
3. Prometheus receives `probe_success = 0`.
4. Prometheus waits for the configured 30 seconds.
5. Prometheus changes the alert to firing.
6. Alertmanager receives the alert.
7. Alertmanager sends an HTTP POST request to Flask.
8. Flask checks the alert name.
9. Flask executes the Ansible playbook.
10. Ansible restarts NGINX.
11. NGINX starts responding again.

This is the self-healing process.

---

## 18. Actual Failure Simulation

Now we test the complete system.

### Step 1: Start the webhook

```bash
sudo python3 /home/ubuntu/self-healing/webhook.py
```

Keep this terminal open.

### Step 2: Stop NGINX

In another terminal:

```bash
sudo systemctl stop nginx
```

This simulates a service failure.

### Step 3: Verify the failure

```bash
curl -I http://localhost
```

Expected result:

A connection error.

This confirms that NGINX is unavailable.

### Step 4: Check Prometheus alerts

```bash
curl -s http://localhost:9090/api/v1/alerts
```

The `NginxDown` alert initially appears as pending.

After the configured 30 seconds, it becomes firing.

### Step 5: Automatic recovery

Alertmanager sends the alert to the webhook.

The webhook executes:

```bash
ansible-playbook /home/ubuntu/self-healing/restart-nginx.yml
```

Ansible restarts NGINX automatically.

### Step 6: Verify recovery

```bash
sudo systemctl status nginx
```

Expected result:

`Active: active (running)`

Check the HTTP response:

```bash
curl -I http://localhost
```

Expected result:

`HTTP/1.1 200 OK`

### Actual project result

We successfully stopped NGINX and observed the complete automatic recovery process.

The Ansible execution completed successfully with:

- `changed=1`
- `failed=0`

NGINX returned to an active state and responded with HTTP 200 OK.

No manual restart was needed.

---

## 19. Project Deliverables

The project requires four main deliverables.

### Deliverable 1: Prometheus Configuration

Files:
- `prometheus.yml`
- `alert-rules.yml`

These files define monitoring targets and alert conditions.

### Deliverable 2: Alertmanager Webhook Setup

Files:
- `alertmanager.yml`
- `webhook.py`

These files configure alert delivery and connect alerts to our automation.

### Deliverable 3: Ansible Playbook

File:
- `restart-nginx.yml`

This file contains the recovery instructions.

### Deliverable 4: Demo Logs and Screenshots

Evidence should include:

1. NGINX failure.
2. Prometheus alert detection.
3. Webhook receiving the alert.
4. Ansible playbook execution.
5. NGINX recovery.

---

## 20. Troubleshooting

### Problem: Prometheus target is down

Check:

```bash
sudo systemctl status prometheus-node-exporter
```

Check the metrics endpoint:

```bash
curl http://localhost:9100/metrics
```

### Problem: NGINX alert does not appear

Check Blackbox Exporter:

```bash
sudo systemctl status prometheus-blackbox-exporter
```

Check the metric:

```bash
curl -sG http://localhost:9090/api/v1/query --data-urlencode 'query=probe_success'
```

### Problem: Alertmanager does not send notifications

Check:

```bash
sudo systemctl status prometheus-alertmanager
```

Check its logs:

```bash
sudo journalctl -u prometheus-alertmanager -n 30 --no-pager
```

### Problem: Webhook does not trigger Ansible

Check that the Flask application is running.

Check the endpoint:

```bash
curl -X POST http://localhost:5001/alert \
-H "Content-Type: application/json" \
-d '{"alerts":[{"status":"firing","labels":{"alertname":"NginxDown"}}]}'
```

This manually tests the webhook.

### Problem: Ansible cannot restart NGINX

Test the playbook manually:

```bash
sudo ansible-playbook /home/ubuntu/self-healing/restart-nginx.yml
```

---

## 21. Final Outcome

Successfully built a self-healing infrastructure system using AWS EC2, Ubuntu, Prometheus, Alertmanager, Python Flask, and Ansible.

The system detects NGINX failures and automatically restores the service without manual intervention.

The NGINX recovery workflow was successfully demonstrated.

The CPU alert rule was configured, but its firing and recovery workflow was not successfully demonstrated during testing.

### What I Learned

Through this project, I learned:

- How to deploy and manage services on AWS EC2.
- How Linux services work.
- How Prometheus collects monitoring metrics.
- How Node Exporter and Blackbox Exporter work.
- How Prometheus alert rules detect failures.
- How Alertmanager handles notifications.
- How Python Flask receives webhooks.
- How Ansible automates infrastructure recovery.
- How to connect monitoring and automation into one workflow.

**The biggest lesson:** Monitoring tells us when something is wrong. Automation helps us fix it.
