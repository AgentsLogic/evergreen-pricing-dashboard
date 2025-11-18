"""
Flask server for the price dashboard with working buttons
"""

import asyncio
import json
import os
import subprocess
import threading
import time
import queue
from pathlib import Path
from flask import Flask, jsonify, send_file, request, Response
from flask_cors import CORS
from datetime import datetime
# File watching functionality (optional)
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("[WARNING] Watchdog not available - file watching disabled")

app = Flask(__name__)
CORS(app)

# Global variable to track scraping status
scraping_status = {
    "running": False,
    "progress": "",
    "last_run": None,
    "error": None
}

# Store the scraper process for stopping
scraper_process = None

# Chat message queue for real-time streaming
chat_message_queue = queue.Queue()
chat_subscribers = []

# Store chat history
chat_history = []

# Data update queue for real-time data streaming
data_update_queue = queue.Queue()

# File watcher for competitor_prices.json (only if watchdog available)
if WATCHDOG_AVAILABLE:
    class DataFileWatcher(FileSystemEventHandler):
        """Watch for changes to competitor_prices.json and notify clients"""

        def on_modified(self, event):
            if event.src_path.endswith('competitor_prices.json'):
                print(f"[WATCHER] Detected change in competitor_prices.json")
                # Notify all SSE clients
                data_update_queue.put({'type': 'data_updated', 'timestamp': datetime.now().isoformat()})

    # Start file watcher
    def start_file_watcher():
        """Start watching the competitor_prices.json file"""
        event_handler = DataFileWatcher()
        observer = Observer()
        observer.schedule(event_handler, path='.', recursive=False)
        observer.start()
        return observer
else:
    # Dummy function when watchdog not available
    def start_file_watcher():
        return None

file_observer = None


@app.route('/')
def index():
    """Serve the dashboard"""
    return send_file('price_dashboard.html')


@app.route('/health')
def health():
    """Health check endpoint for container health probes"""
    return jsonify({"status": "ok"}), 200



@app.route('/api/data')
def get_data():
    """Get the current competitor prices data"""
    try:
        data_file = Path('competitor_prices.json')
        if data_file.exists():
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        else:
            return jsonify({"error": "No data file found. Run the scraper first."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/scrape/status')
def scrape_status():
    """Get the current scraping status"""
    return jsonify(scraping_status)


@app.route('/api/scrape/start', methods=['POST'])
def start_scrape():
    """Start the scraping process"""
    global scraping_status

    if scraping_status["running"]:
        return jsonify({"error": "Scraper is already running"}), 400

    # Get scraper type and site from request
    data = request.get_json() or {}
    scraper_type = data.get('type', 'basic')  # 'basic' or 'advanced'
    site = data.get('site', 'all')  # 'all' or specific site name

    # Start scraping in background thread
    thread = threading.Thread(target=run_scraper, args=(scraper_type, site))
    thread.daemon = True
    thread.start()

    return jsonify({
        "message": "Scraper started",
        "type": scraper_type,
        "site": site
    })


@app.route('/api/scrape/stop', methods=['POST'])
def stop_scrape():
    """Stop the currently running scraper"""
    global scraping_status, scraper_process

    if not scraping_status["running"]:
        return jsonify({"error": "No scraper is currently running"}), 400

    try:
        if scraper_process and scraper_process.poll() is None:
            # Terminate the process
            scraper_process.terminate()

            # Wait up to 5 seconds for graceful termination
            try:
                scraper_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate gracefully
                scraper_process.kill()
                scraper_process.wait()

            scraping_status["running"] = False
            scraping_status["progress"] = "Stopped by user"
            send_chat_message_sync("🛑 Scraper stopped by user", "warning", "system")

            return jsonify({"message": "Scraper stopped successfully"})
        else:
            return jsonify({"error": "Scraper process not found or already finished"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to stop scraper: {str(e)}"}), 500


def run_scraper(scraper_type='basic', site='all'):
    """Run the scraper in background"""
    global scraping_status, scraper_process

    scraping_status["running"] = True
    scraping_status["progress"] = "Starting scraper..."
    scraping_status["error"] = None

    # Send initial chat message
    site_text = "all sites" if site == 'all' else site
    send_chat_message_sync(f"🚀 Starting {scraper_type} scraper for {site_text}...", "info", "scraper")

    try:
        # Always use the new scraper_v2.py
        scraping_status["progress"] = f"Running AI-powered scraper..."
        send_chat_message_sync("🔍 Running AI-powered web scraper (scraper_v2.py)...", "info", "scraper")
        script = 'scraper_v2.py'

        # Ensure required modules are available in all branches
        import subprocess
        import sys
        import threading


        # Pass site parameters if specified
        if site != 'all':

            def stream_output(proc, message_type="info"):
                """Stream real-time output to chat"""
                try:
                    while True:
                        if proc.poll() is not None:
                            break
                        # Check stdout
                        if hasattr(proc.stdout, 'readline'):
                            try:
                                line = proc.stdout.readline()
                                if line:
                                    # Handle both string and bytes
                                    if isinstance(line, bytes):
                                        decoded_line = line.strip().decode('utf-8', errors='replace')
                                    else:
                                        decoded_line = str(line).strip()

                                    if decoded_line:  # Only send non-empty lines
                                        send_chat_message_sync(decoded_line, message_type, "scraper")
                            except (UnicodeDecodeError, AttributeError) as e:
                                send_chat_message_sync(f"Line processing error: {str(e)}", "warning", "scraper")
                        else:
                            break

                        import time
                        time.sleep(0.1)  # Prevent tight loop
                except Exception as e:
                    send_chat_message_sync(f"Stream error: {str(e)}", "warning", "scraper")

            # Build command with site filter
            # Use -u flag for unbuffered output
            cmd = [sys.executable, '-u', script]
            if site != 'all':
                cmd.extend(['--competitor', site])

            send_chat_message_sync(f"⚡ Executing: python -u {script} --competitor {site}", "info", "scraper")
            send_chat_message_sync("📋 Scraping single competitor with pagination...", "info", "scraper")

            # Set environment variable to force unbuffered output
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'

            # Start process with pipes for real-time output
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,  # Unbuffered
                universal_newlines=True,
                cwd=os.getcwd(),
                encoding='utf-8',
                errors='replace',  # Handle encoding errors gracefully
                env=env
            )

            # Store process globally for stop functionality
            scraper_process = proc
            send_chat_message_sync(f"✅ Process started (PID: {proc.pid})", "success", "scraper")

            # Start streaming output in background thread
            stream_thread = threading.Thread(target=stream_output, args=(proc,))
            stream_thread.daemon = True
            stream_thread.start()

            # Wait for completion with timeout
            proc.wait(timeout=1800)  # 30 minute timeout

            if proc.returncode == 0:
                scraping_status["progress"] = "Scraping completed successfully!"
                scraping_status["last_run"] = datetime.now().isoformat()
                send_chat_message_sync("✅ Scraping completed successfully!", "success", "scraper")
            else:
                scraping_status["error"] = "Scraping failed - check logs"
                scraping_status["progress"] = "Scraping failed"
                send_chat_message_sync("❌ Scraping failed - check error logs", "error", "scraper")

            # Finished (single-site)
            send_chat_message_sync(f"🏁 Scraper process finished (exit={proc.returncode})", "info", "scraper")
            scraping_status["running"] = False
            return

        elif site == 'all':
            # Optional: warn if no .env (we can still run without AI key)
            env_file = Path('.env')
            if not env_file.exists():
                warn_msg = "No .env found — proceeding without AI key; extraction may be less accurate."
                scraping_status["error"] = None
                send_chat_message_sync(f"⚠️ {warn_msg}", "warning", "scraper")


            # Use same streaming approach as single-site for real-time output
            import sys

            def stream_output(proc, message_type="info"):
                """Stream real-time output to chat - SAME AS SINGLE-SITE VERSION"""
                try:
                    while True:
                        if proc.poll() is not None:
                            break
                        # Check stdout
                        if hasattr(proc.stdout, 'readline'):
                            try:
                                line = proc.stdout.readline()
                                if line:
                                    # Handle both string and bytes
                                    if isinstance(line, bytes):
                                        decoded_line = line.strip().decode('utf-8', errors='replace')
                                    else:
                                        decoded_line = str(line).strip()

                                    if decoded_line:  # Only send non-empty lines
                                        # Determine message type based on content
                                        if any(x in decoded_line for x in ['ERROR', 'FAILED', 'Exception']):
                                            msg_type = "error"
                                        elif any(x in decoded_line for x in ['WARNING', 'WARN']):
                                            msg_type = "warning"
                                        elif any(x in decoded_line for x in ['SUCCESS', '✅', 'COMPLETED']):
                                            msg_type = "success"
                                        else:
                                            msg_type = "info"

                                        send_chat_message_sync(decoded_line, msg_type, "scraper")
                            except (UnicodeDecodeError, AttributeError) as e:
                                send_chat_message_sync(f"Line processing error: {str(e)}", "warning", "scraper")
                        else:
                            break

                        import time
                        time.sleep(0.1)  # Prevent tight loop
                except Exception as e:
                    send_chat_message_sync(f"Stream error: {str(e)}", "warning", "scraper")

            # Build command - Use -u flag for unbuffered output
            cmd = [sys.executable, '-u', script]

            send_chat_message_sync(f"⚡ Executing: python -u {script}", "info", "scraper")
            send_chat_message_sync("📋 Scraping all 5 competitors with pagination...", "info", "scraper")

            # Set environment variable to force unbuffered output
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'

            # Start process with pipes for real-time output
            # IMPORTANT: Use stderr=subprocess.STDOUT to merge stderr into stdout (SAME AS SINGLE-SITE)
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,  # Unbuffered
                universal_newlines=True,
                cwd=os.getcwd(),
                encoding='utf-8',
                errors='replace',
                env=env
            )

            # Store process globally for stop functionality
            scraper_process = proc

            send_chat_message_sync(f"✅ Process started (PID: {proc.pid})", "success", "scraper")
            send_chat_message_sync(f"⏳ Waiting for scraper to complete (this may take 30+ minutes)...", "info", "scraper")

            # Start streaming output in background thread
            stream_thread = threading.Thread(target=stream_output, args=(proc,))
            stream_thread.daemon = True
            stream_thread.start()

            # Wait for completion with timeout
            proc.wait(timeout=1800)  # 30 minute timeout

            # Wait for thread to finish reading any remaining output
            stream_thread.join(timeout=5)

            if proc.returncode == 0:
                scraping_status["progress"] = "Scraping completed successfully!"
                scraping_status["last_run"] = datetime.now().isoformat()
                send_chat_message_sync("✅ Scraping completed successfully!", "success", "scraper")
            else:
                scraping_status["error"] = "Scraping failed - check logs"
                scraping_status["progress"] = "Scraping failed"
                send_chat_message_sync("❌ Scraping failed - check error logs", "error", "scraper")

            # Finished (all sites)
            send_chat_message_sync(f"🏁 Scraper process finished (exit={proc.returncode})", "info", "scraper")

    except subprocess.TimeoutExpired:
        error_msg = "Scraper timed out after 30 minutes"
        scraping_status["error"] = error_msg
        scraping_status["progress"] = "Timeout"
        send_chat_message_sync(f"⏰ {error_msg}", "error", "scraper")
    except Exception as e:
        error_msg = str(e)
        scraping_status["error"] = error_msg
        scraping_status["progress"] = "Error occurred"
        send_chat_message_sync(f"💥 Error occurred: {error_msg}", "error", "scraper")

    finally:
        scraping_status["running"] = False


@app.route('/api/test')
def test_scraper():
    """Run a quick test scrape"""
    try:
        result = subprocess.run(
            ['python', 'test_scraper.py'],
            capture_output=True,
            text=True,
            timeout=60,
            input='1\n',  # Choose option 1
            encoding='utf-8',
            errors='replace'  # Handle encoding errors gracefully
        )

        return jsonify({
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/config')
def get_config():
    """Get current configuration"""
    env_file = Path('.env')

    config = {
        "has_env_file": env_file.exists(),
        "has_deepseek_key": bool(os.getenv("DEEPSEEK_API_KEY")),
        "has_openai_key": bool(os.getenv("OPENAI_API_KEY")),
        "provider": os.getenv("LLM_PROVIDER", "deepseek")
    }

    return jsonify(config)


@app.route('/api/data/stream')
def data_stream():
    """Server-Sent Events endpoint for real-time data updates"""

    def generate():
        """Generate SSE events when data file changes"""
        while True:
            try:
                # Get update notification from queue with timeout
                update_data = data_update_queue.get(timeout=1)

                # Format as SSE
                event_data = f"data: {json.dumps(update_data)}\n\n"
                yield event_data

            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield "data: {\"type\": \"heartbeat\"}\n\n"
                time.sleep(1)

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/chat/stream')
def chat_stream():
    """Server-Sent Events endpoint for real-time chat messages"""

    def generate():
        """Generate SSE events for chat messages"""
        while True:
            try:
                # Get message from queue with timeout
                message_data = chat_message_queue.get(timeout=1)

                # Format as SSE
                timestamp = datetime.now().isoformat()
                event_data = f"data: {json.dumps({**message_data, 'timestamp': timestamp})}\n\n"
                yield event_data

            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield "data: {\"type\": \"heartbeat\"}\n\n"
                time.sleep(1)

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/chat/send', methods=['POST'])
def send_chat_message():
    """Send a message to the chat"""
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "Message is required"}), 400

    message = data['message']
    message_type = data.get('type', 'info')

    # Create message data
    message_data = {
        'message': message,
        'type': message_type,
        'source': 'api'
    }

    # Add to queue for streaming
    chat_message_queue.put(message_data)

    # Add to history
    chat_history.append({
        'timestamp': datetime.now().isoformat(),
        'message': message,
        'type': message_type,
        'source': 'api'
    })

    # Keep only last 1000 messages in history
    if len(chat_history) > 1000:
        chat_history.pop(0)

    return jsonify({"success": True})


@app.route('/api/chat/history')
def get_chat_history():
    """Get chat history"""
    return jsonify({
        'messages': chat_history,
        'count': len(chat_history)
    })


@app.route('/api/chat/clear', methods=['POST'])
def clear_chat():
    """Clear chat history"""
    global chat_history
    chat_history = []

    # Send clear message to all subscribers
    clear_message = {
        'message': 'Chat cleared',
        'type': 'warning',
        'source': 'system'
    }
    chat_message_queue.put(clear_message)

    return jsonify({"success": True})


@app.route('/api/multi-site')
def get_multi_site_products():
    """Get products that appear on multiple sites with price comparisons"""
    try:
        data_file = Path('competitor_prices.json')
        if not data_file.exists():
            return jsonify({"error": "No data file found. Run the scraper first."}), 404

        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Process data to find products across multiple sites using intelligent matching
        product_groups = {}

        for competitor_name, competitor_data in data.items():
            for product in competitor_data.get('products', []):
                # Create a normalized product signature for matching
                signature = create_product_signature(product)

                if signature not in product_groups:
                    product_groups[signature] = {
                        'brand': product['brand'],
                        'model': product['model'],
                        'product_type': product.get('product_type', ''),
                        'title': product['title'],
                        'normalized_specs': extract_normalized_specs(product),
                        'sites': {}
                    }

                # Use a compound key to ensure each site only appears once per product
                site_key = f"{competitor_name}_{product['url']}"

                # Only add if this exact site+URL combination doesn't exist
                if site_key not in product_groups[signature]['sites']:
                    product_groups[signature]['sites'][site_key] = {
                        'competitor': competitor_name,
                        'price': product['price'],
                        'url': product['url'],
                        'availability': product.get('availability', 'Available'),
                        'raw_config': product.get('config', {})
                    }

        # Filter to only include products that appear on multiple sites
        multi_site_products = []
        for signature, product_data in product_groups.items():
            # Convert sites dict back to list for API response
            sites_list = list(product_data['sites'].values())

            if len(sites_list) > 1:
                # Sort sites by price for better comparison
                sites_list.sort(key=lambda x: x['price'] if x['price'] else 999999)

                # Calculate price statistics
                prices = [site['price'] for site in sites_list if site['price']]
                if prices:
                    lowest_price = min(prices)
                    highest_price = max(prices)
                    price_range = highest_price - lowest_price
                    avg_price = sum(prices) / len(prices)
                else:
                    lowest_price = None
                    highest_price = None
                    price_range = None
                    avg_price = None

                multi_site_products.append({
                    'brand': product_data['brand'],
                    'model': product_data['model'],
                    'product_type': product_data['product_type'],
                    'title': product_data['title'],
                    'normalized_specs': product_data['normalized_specs'],
                    'sites': sites_list,
                    'lowest_price': lowest_price,
                    'highest_price': highest_price,
                    'price_range': price_range,
                    'avg_price': avg_price
                })

        # Sort by price range (biggest savings first) to show most valuable comparisons
        multi_site_products.sort(key=lambda x: x.get('price_range', 0) or 0, reverse=True)

        return jsonify({
            'products': multi_site_products,
            'total_products': len(multi_site_products),
            'total_unique_products': len(product_groups)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def create_product_signature(product):
    """Create a normalized signature for product matching"""
    brand = normalize_brand(product['brand'])
    model = normalize_model(product['model'])
    product_type = product.get('product_type', '').lower()

    # Extract and normalize key specifications
    config = product.get('config', {})

    # Normalize processor but keep model details
    processor = normalize_processor_detailed(config.get('processor', ''))

    # Normalize RAM but keep size details
    ram = normalize_ram_detailed(config.get('ram', ''))

    # Normalize storage but keep size details
    storage = normalize_storage_detailed(config.get('storage', ''))

    # Create signature based on key components
    # Include RAM and storage even for Dell Latitude 5320 to differentiate configurations
    signature_parts = [
        brand,
        model,
        product_type,
        processor if processor else None,
        ram if ram else None,
        storage if storage else None
    ]

    # Filter out None/empty values and join
    return "_".join(filter(None, signature_parts))


def normalize_brand(brand):
    """Normalize brand names"""
    if not brand:
        return ""

    brand_lower = brand.lower().strip()

    # Handle common variations
    if 'dell' in brand_lower:
        return 'dell'
    elif 'hp' in brand_lower or 'hewlett' in brand_lower:
        return 'hp'
    elif 'lenovo' in brand_lower:
        return 'lenovo'

    return brand_lower


def normalize_model(model):
    """Normalize model names"""
    if not model:
        return ""

    # Remove common prefixes/suffixes and normalize
    model = model.lower().strip()

    # Special handling for Dell Latitude 5320 Touch
    if 'latitude' in model and '5320' in model:
        return '5320touch'

    # Extract core model number (e.g., "ThinkPad T490" -> "t490")
    import re

    # Look for patterns like T490, X1 Carbon, etc.
    model_patterns = [
        r'thinkpad\s+(\w+)',
        r'latitude\s+(\w+)',
        r'elitebook\s+(\w+)',
        r'optiplex\s+(\w+)',
        r'precision\s+(\w+)',
        r'(\w+\s*\d+)',  # Generic model with number
    ]

    for pattern in model_patterns:
        match = re.search(pattern, model, re.IGNORECASE)
        if match:
            return match.group(1).lower().replace(' ', '')

    return model.replace(' ', '')


def normalize_processor(processor):
    """Normalize processor names"""
    if not processor:
        return ""

    processor = processor.lower().strip()

    # Extract core processor info
    if 'i3' in processor:
        return 'i3'
    elif 'i5' in processor:
        return 'i5'
    elif 'i7' in processor:
        return 'i7'
    elif 'i9' in processor:
        return 'i9'
    elif 'ryzen' in processor and '3' in processor:
        return 'ryzen3'
    elif 'ryzen' in processor and '5' in processor:
        return 'ryzen5'
    elif 'ryzen' in processor and '7' in processor:
        return 'ryzen7'
    elif 'celeron' in processor:
        return 'celeron'
    elif 'pentium' in processor:
        return 'pentium'

    return processor[:20]  # Fallback to first 20 chars


def normalize_processor_detailed(processor):
    """Normalize processor names but keep specific model details"""
    if not processor:
        return ""

    processor = processor.lower().strip()

    # Extract specific processor models
    import re

    # Intel processors with specific models
    intel_patterns = [
        r'i3-(\d+)', r'i5-(\d+)', r'i7-(\d+)', r'i9-(\d+)',
        r'intel\s+core\s+i3-(\d+)', r'intel\s+core\s+i5-(\d+)',
        r'intel\s+core\s+i7-(\d+)', r'intel\s+core\s+i9-(\d+)'
    ]

    for pattern in intel_patterns:
        match = re.search(pattern, processor)
        if match:
            return f"i{match.group(1)[0]}{match.group(1)[1:]}"

    # AMD Ryzen processors
    ryzen_patterns = [
        r'ryzen\s+(\d+)\s*(\d+)?', r'amd\s+ryzen\s+(\d+)\s*(\d+)?'
    ]

    for pattern in ryzen_patterns:
        match = re.search(pattern, processor)
        if match:
            ryzen_num = match.group(1)
            model_num = match.group(2) if match.group(2) else ''
            return f"ryzen{ryzen_num}{model_num}"

    # Other processor types
    if 'celeron' in processor:
        return 'celeron'
    elif 'pentium' in processor:
        return 'pentium'
    elif 'xeon' in processor:
        return 'xeon'

    return processor[:30]  # Fallback to first 30 chars


def normalize_ram_detailed(ram):
    """Normalize RAM specification but keep size details"""
    if not ram:
        return ""

    import re

    # Extract RAM size and type
    ram_match = re.search(r'(\d+)\s*(gb|mb)', str(ram).lower())
    if ram_match:
        size = ram_match.group(1)
        unit = ram_match.group(2)
        return f"{size}{unit}"

    # Just look for number
    number_match = re.search(r'(\d+)', str(ram))
    if number_match:
        return f"{number_match.group(1)}gb"

    return str(ram)[:20]


def normalize_storage_detailed(storage):
    """Normalize storage specification but keep size details"""
    if not storage:
        return ""

    import re
    storage = storage.lower().strip()

    # Extract size and unit
    size_match = re.search(r'(\d+(?:\.\d+)?)\s*(gb|tb|mb)', storage)
    if size_match:
        size = size_match.group(1)
        unit = size_match.group(2)
        return f"{size}{unit}"

    # Look for just numbers with storage context
    if any(word in storage for word in ['ssd', 'hdd', 'nvme', 'sata']):
        number_match = re.search(r'(\d+)', storage)
        if number_match:
            return f"{number_match.group(1)}gb"

    return storage[:30]  # Fallback


def normalize_ram(ram):
    """Normalize RAM specification"""
    if not ram:
        return ""

    import re
    ram_match = re.search(r'(\d+)', str(ram))
    if ram_match:
        return f"{ram_match.group(1)}gb"

    return ""


def normalize_storage(storage):
    """Normalize storage specification"""
    if not storage:
        return ""

    import re
    storage = storage.lower().strip()

    # Extract size and type
    size_match = re.search(r'(\d+)', storage)
    if size_match:
        size = size_match.group(1)
        if 'tb' in storage or 'tera' in storage:
            return f"{size}tb"
        elif 'gb' in storage or 'ssd' in storage or 'hdd' in storage:
            return f"{size}gb"

    return storage[:20]  # Fallback


def extract_normalized_specs(product):
    """Extract normalized specifications for display"""
    config = product.get('config', {})

    specs = {
        'processor': config.get('processor', 'Not specified'),
        'ram': config.get('ram', 'Not specified'),
        'storage': config.get('storage', 'Not specified'),
        'screen_resolution': config.get('screen_resolution', 'Not specified') if product.get('product_type') == 'Laptop' else None,
        'form_factor': config.get('form_factor', 'Not specified') if product.get('product_type') == 'Desktop' else None,
        'cosmetic_grade': config.get('cosmetic_grade', 'Not specified')
    }

    return specs


@app.route('/multi-site-comparison')
def multi_site_comparison():
    """Serve the multi-site product comparison page"""
    return send_file('multi_site_comparison.html')


@app.route('/graphs')
def graphs_dashboard():
    """Serve the graphs dashboard page"""
    return send_file('graphs_dashboard.html')


@app.route('/popularity')
def popularity_dashboard():
    """Serve the popularity rankings dashboard page"""
    return send_file('popularity_dashboard.html')


def send_chat_message_sync(message, message_type='info', source='system'):
    """Helper function to send chat messages from other threads"""
    message_data = {
        'message': message,
        'type': message_type,
        'source': source
    }

    # Add to queue for streaming
    try:
        chat_message_queue.put_nowait(message_data)
    except queue.Full:
        # Remove oldest message if queue is full
        try:
            chat_message_queue.get_nowait()
            chat_message_queue.put_nowait(message_data)
        except queue.Empty:
            pass

    # Add to history
    chat_history.append({
        'timestamp': datetime.now().isoformat(),
        'message': message,
        'type': message_type,
        'source': source
    })

    # Keep only last 1000 messages in history
    if len(chat_history) > 1000:
        chat_history.pop(0)


if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 Starting Competitor Price Dashboard Server")
    print("="*80)
    print("\n📊 Dashboard URL: http://localhost:8080")
    print("\n✅ Features:")
    print("   - Real-time data updates (no refresh needed!)")
    print("   - Live chat output from scraper")
    print("   - Export CSV, Run Scraper, and more!")
    print("\n🔍 Starting file watcher for real-time updates...")
    print("="*80 + "\n")

    # Start file watcher for real-time updates (if available)
    if WATCHDOG_AVAILABLE:
        file_observer = start_file_watcher()
        print("[WATCHER] File watcher started - monitoring competitor_prices.json")
    else:
        file_observer = None
        print("[WATCHER] File watcher disabled - watchdog not available")

    try:
        app.run(debug=True, port=8080, host='0.0.0.0', use_reloader=False)
    finally:
        if file_observer:
            file_observer.stop()
            file_observer.join()
            print("[WATCHER] File watcher stopped")
