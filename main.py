import smtplib
import time
import threading
from flask import Flask, request, render_template, redirect, url_for
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Server Configuration
HEARTBEAT_TIMEOUT = 30  # Timeout in seconds
EMAIL_SENDER = "tobias.ober2008@gmail.com"
EMAIL_RECEIVER = "tobias.oberegger2008@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_PASSWORD = "your_email_password_here"  # Replace with your app-specific password

# Flask App Setup
app = Flask(__name__)
monitors_file = 'monitors.json'

def load_monitors():
    with open(monitors_file, 'r') as file:
        return json.load(file)

def save_monitors(monitors):
    with open(monitors_file, 'w') as file:
        json.dump(monitors, file, indent=4)

@app.route('/')
def index():
    monitors = load_monitors()
    current_time = time.time()
    for monitor in monitors.values():
        monitor["offline"] = (current_time - monitor["last_heartbeat"]) > HEARTBEAT_TIMEOUT
    return render_template('index.html', monitors=monitors)

@app.route('/update_location/<monitor_name>', methods=['POST'])
def update_location(monitor_name):
    new_location = request.form['location']
    monitors = load_monitors()
    if monitor_name in monitors:
        monitors[monitor_name]["location"] = new_location
        save_monitors(monitors)
    return redirect(url_for('index'))

@app.route('/send_heartbeat/<monitor_name>', methods=['POST'])
def send_heartbeat(monitor_name):
    monitors = load_monitors()
    if monitor_name in monitors:
        monitors[monitor_name]["last_heartbeat"] = time.time()
        monitors[monitor_name]["offline"] = False
        save_monitors(monitors)
    return redirect(url_for('index'))

@app.route('/heartbeat', methods=['POST'])
def receive_heartbeat():
    monitor_data = request.json
    monitor_name = monitor_data.get("monitor_name")
    alias = monitor_data.get("alias")
    location = monitor_data.get("location")

    monitors = load_monitors()
    if monitor_name:
        monitors[monitor_name] = {
            "last_heartbeat": time.time(),
            "alias": alias,
            "location": location,
            "offline": False
        }
        save_monitors(monitors)
    return "Heartbeat received", 200

def send_email(monitor_name, alias, location):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Monitor-Status: Offline ({monitor_name})"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    # Create the HTML email content
    html = f"""
    <html>
      <body>
        <div style='border: 1px solid #ddd; padding: 20px;'>
          <h2 style='color: #d9534f;'>Monitor-Status: Offline</h2>
          <p><strong>Monitor-Name:</strong> {monitor_name}</p>
          <p><strong>Alias:</strong> {alias}</p>
          <p><strong>Standort:</strong> {location}</p>
          <p><strong>Bemerkung:</strong> Der Monitor scheint offline zu sein und hat sich seit über 30 Sekunden nicht gemeldet.</p>
        </div>
      </body>
    </html>
    """
    msg.attach(MIMEText(html, 'html'))

    # Send the email
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print(f"Email sent successfully for monitor: {monitor_name}")
    except Exception as e:
        print(f"Failed to send email for monitor {monitor_name}: {e}")

def monitor_status():
    while True:
        monitors = load_monitors()
        current_time = time.time()
        for monitor_name, data in monitors.items():
            if current_time - data["last_heartbeat"] > HEARTBEAT_TIMEOUT and not data["offline"]:
                send_email(monitor_name, data["alias"], data["location"])
                data["offline"] = True
        save_monitors(monitors)
        time.sleep(1)

# Start the monitoring thread
monitor_thread = threading.Thread(target=monitor_status)
monitor_thread.daemon = True
monitor_thread.start()

if __name__ == '__main__':
    app.run(host='192.84.22.03', port=5000)
