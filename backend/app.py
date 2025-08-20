from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import subprocess
import os
import json
from datetime import datetime, timedelta
import re
from threading import Thread
import time
import schedule
import sys

app = Flask(__name__)
CORS(app)

# Configuration
DEBUG_MODE = True  # Set to False to use actual lmstat.exe
LMSTAT_COMMAND = "lmstat.exe -c 29000@hqcndb -a"
LOGS_DIR = "logs"
DEBUG_FILE = "234.txt"
UPDATE_INTERVAL = 1  # minutes

class LicenseMonitor:
    def __init__(self):
        self.last_update = None
        self.health_status = []
        self.max_health_records = 100
        
        # Ensure logs directory exists
        if not os.path.exists(LOGS_DIR):
            os.makedirs(LOGS_DIR)
    
    def execute_lmstat(self):
        """Execute lmstat command or read debug file"""
        try:
            if DEBUG_MODE:
                # Read from debug file
                with open(resource_path(DEBUG_FILE), 'r', encoding='utf-8') as f:
                    output = f.read()
            else:
                # Execute actual command
                result = subprocess.run(LMSTAT_COMMAND, shell=True, 
                                      capture_output=True, text=True, 
                                      timeout=60)
                if result.returncode != 0:
                    raise Exception(f"Command failed: {result.stderr}")
                output = result.stdout
            
            # Save to log file with timestamp
            timestamp = datetime.now()
            filename = timestamp.strftime("%Y%m%d_%H%M%S.txt")
            filepath = os.path.join(LOGS_DIR, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(output)
            
            self.last_update = timestamp
            self.health_status.append({
                'timestamp': timestamp.isoformat(),
                'status': 'success'
            })
            
            # Keep only last 100 health records
            if len(self.health_status) > self.max_health_records:
                self.health_status = self.health_status[-self.max_health_records:]
            
            print(f"License data collected at {timestamp}")
            return True
            
        except Exception as e:
            self.health_status.append({
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            })
            print(f"Error collecting license data: {e}")
            return False
    
    def parse_license_data(self, content):
        """Parse license usage data from lmstat output"""
        licenses = []
        lines = content.split('\n')
        
        current_feature = None
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Match feature usage lines
            feature_match = re.match(r'Users of ([^:]+):\s+\(Total of (\d+) licenses issued;\s+Total of (\d+) licenses? in use\)', line)
            if feature_match:
                feature_name = feature_match.group(1)
                total_licenses = int(feature_match.group(2))
                licenses_in_use = int(feature_match.group(3))
                
                current_feature = {
                    'feature': feature_name,
                    'total': total_licenses,
                    'in_use': licenses_in_use,
                    'available': total_licenses - licenses_in_use,
                    'users': []
                }
                licenses.append(current_feature)
                
                # If there are licenses in use, look for user details in following lines
                if licenses_in_use > 0:
                    j = i + 1
                    # Skip the feature description lines (like "solid_modeling" v2024.12, vendor: ugslmd)
                    while j < len(lines) and not lines[j].strip().startswith('Users of'):
                        detail_line = lines[j].strip()
                        
                        # Look for user detail lines (they typically start with a username)
                        # Pattern: username hostname details (HQCNDB/29000 port), start date time (linger: number)
                        user_match = re.match(r'^(\w+)\s+([^\s]+)\s+.*?\(([^)]+)\),\s*start\s+(.+?)\s*\(linger:\s*(\d+)\)', detail_line)
                        if user_match:
                            username = user_match.group(1)
                            hostname = user_match.group(2)
                            connection_info = user_match.group(3)
                            start_time = user_match.group(4)
                            linger_time = user_match.group(5)
                            
                            user_info = {
                                'user': username,
                                'host': hostname,
                                'connection': connection_info,
                                'start_time': start_time,
                                'linger': linger_time,
                                'details': detail_line
                            }
                            current_feature['users'].append(user_info)
                        
                        j += 1
                        # Break if we hit the next "Users of" line
                        if j < len(lines) and lines[j].strip().startswith('Users of'):
                            break
                    
                    i = j - 1  # Adjust index to continue from the right position
            
            i += 1
        
        return licenses
    
    def get_user_statistics(self, licenses):
        """Generate user-based statistics"""
        user_stats = {}
        for license in licenses:
            if license['users']:
                for user in license['users']:
                    username = user['user']
                    if username not in user_stats:
                        user_stats[username] = {
                            'username': username,
                            'total_licenses': 0,
                            'licenses': [],
                            'hosts': set(),
                            'first_seen': user.get('start_time', 'Unknown'),
                            'connections': []
                        }
                    
                    user_stats[username]['total_licenses'] += 1
                    user_stats[username]['licenses'].append({
                        'feature': license['feature'],
                        'host': user['host'],
                        'start_time': user.get('start_time', 'Unknown'),
                        'connection': user.get('connection', 'Unknown')
                    })
                    user_stats[username]['hosts'].add(user['host'])
                    if user.get('connection'):
                        user_stats[username]['connections'].append(user['connection'])
        
        # Convert sets to lists for JSON serialization
        for user in user_stats.values():
            user['hosts'] = list(user['hosts'])
            user['unique_hosts'] = len(user['hosts'])
        
        return list(user_stats.values())
    
    def get_module_statistics(self, licenses):
        """Generate module-based statistics"""
        module_stats = []
        for license in licenses:
            if license.get('in_use', 0) > 0 or license.get('peak_usage', 0) > 0:  # Include if ever used in period
                module_info = {
                    'feature': license['feature'],
                    'total': license['total'],
                    'in_use': license.get('in_use', 0), # Current in_use
                    'available': license['total'] - license.get('in_use', 0),
                    'usage_rate': (license.get('in_use', 0) / license['total'] * 100) if license['total'] > 0 else 0,
                    'users': license.get('users', []),
                    'peak_usage': license.get('peak_usage', 0),
                    'total_duration_minutes': license.get('total_duration_minutes', 0)
                }
                module_stats.append(module_info)
        
        # Sort by peak usage descending
        module_stats.sort(key=lambda x: x['peak_usage'], reverse=True)
        return module_stats

    def get_historical_summary(self, time_filter='week'):
        """Get historical summary of license usage."""
        log_files = self.get_log_files(time_filter)
        
        # We want chronological order, so reverse the list
        log_files.reverse()
        
        summary_data = []
        
        for log_file in log_files:
            try:
                with open(log_file['filepath'], 'r', encoding='utf-8') as f:
                    content = f.read()
                
                licenses = self.parse_license_data(content)
                
                total_licenses_in_use = sum(l['in_use'] for l in licenses)
                
                # To get unique users, we need to aggregate them first
                user_stats = self.get_user_statistics(licenses)
                total_users = len(user_stats)
                
                summary_data.append({
                    'timestamp': log_file['timestamp'],
                    'total_licenses_in_use': total_licenses_in_use,
                    'total_users': total_users
                })
            except Exception as e:
                print(f"Error processing log file {log_file['filename']}: {e}")
                # Optionally skip corrupted files
                continue
                
        return summary_data
    
    def get_log_files(self, time_filter='latest'):
        """Get log files based on time filter"""
        all_files = []
        for filename in os.listdir(LOGS_DIR):
            if filename.endswith('.txt'):
                filepath = os.path.join(LOGS_DIR, filename)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    all_files.append({
                        'filename': filename,
                        'filepath': filepath,
                        'timestamp': mtime.isoformat(),
                        'size': os.path.getsize(filepath)
                    })
                except FileNotFoundError:
                    # File might be deleted between listdir and getmtime
                    continue
        
        # Sort by timestamp descending to find the latest files first
        all_files.sort(key=lambda x: x['timestamp'], reverse=True)

        if time_filter == 'latest':
            return all_files[:1]

        now = datetime.now()
        if time_filter == 'week':
            week_ago = now - timedelta(days=7)
            return [f for f in all_files if datetime.fromisoformat(f['timestamp']) >= week_ago]
        
        if time_filter == 'month':
            month_ago = now - timedelta(days=30)
            return [f for f in all_files if datetime.fromisoformat(f['timestamp']) >= month_ago]
        
        # Fallback for unknown filter, return all
        return all_files
    
    def get_latest_license_data(self):
        """Get parsed license data from latest log file"""
        files = self.get_log_files('latest')
        if not files:
            return None
        
        latest_file = files[0]
        with open(latest_file['filepath'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        licenses = self.parse_license_data(content)
        return {
            'timestamp': latest_file['timestamp'],
            'licenses': licenses,
            'raw_content': content
        }

    def get_aggregated_license_data(self, time_filter='latest'):
        """Get aggregated license data from log files based on time filter"""
        if time_filter == 'latest':
            data = self.get_latest_license_data()
            if data and data.get('licenses'):
                for lic in data['licenses']:
                    lic['peak_usage'] = lic['in_use']
                    lic['total_duration_minutes'] = UPDATE_INTERVAL if lic['in_use'] > 0 else 0
            return data

        log_files = self.get_log_files(time_filter)
        if not log_files:
            return None

        aggregated_licenses = {}
        all_raw_content = []
        latest_timestamp = log_files[0]['timestamp'] if log_files else "N/A"

        for log_file in log_files:
            try:
                with open(log_file['filepath'], 'r', encoding='utf-8') as f:
                    content = f.read()
                    all_raw_content.append(f"--- Log from {log_file['filename']} ---\n{content}")
                
                licenses = self.parse_license_data(content)
                
                for license_data in licenses:
                    feature = license_data['feature']
                    if feature not in aggregated_licenses:
                        aggregated_licenses[feature] = {
                            'feature': feature,
                            'total': 0,
                            'peak_usage': 0,
                            'total_duration_minutes': 0,
                            'users': {}
                        }
                    
                    agg_license = aggregated_licenses[feature]
                    agg_license['total'] = max(agg_license['total'], license_data['total'])
                    agg_license['peak_usage'] = max(agg_license['peak_usage'], license_data['in_use'])
                    
                    # Add duration for each user found in this log file
                    if license_data['in_use'] > 0:
                        agg_license['total_duration_minutes'] += UPDATE_INTERVAL * license_data['in_use']

                    for user in license_data['users']:
                        user_key = f"{user['user']}|{user['host']}"
                        if user_key not in agg_license['users']:
                             agg_license['users'][user_key] = user

            except Exception as e:
                print(f"Error processing log file for aggregation {log_file['filename']}: {e}")
                continue
        
        # Get latest 'in_use' count from the most recent file
        latest_data = self.get_latest_license_data()
        latest_licenses = {lic['feature']: lic for lic in latest_data.get('licenses', [])}

        final_licenses = []
        for feature, data in aggregated_licenses.items():
            data['users'] = list(data['users'].values())
            
            # Set current 'in_use' from the latest data
            if feature in latest_licenses:
                data['in_use'] = latest_licenses[feature]['in_use']
            else:
                data['in_use'] = 0
            
            data['available'] = data['total'] - data['in_use']
            final_licenses.append(data)

        return {
            'timestamp': latest_timestamp,
            'licenses': final_licenses,
            'raw_content': "\n".join(all_raw_content)
        }

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # In development, the base path is the project root (one level up from this script)
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    return os.path.join(base_path, relative_path)

# Initialize monitor
monitor = LicenseMonitor()

# Scheduled task
def scheduled_task():
    monitor.execute_lmstat()

# Schedule the task
schedule.every(UPDATE_INTERVAL).minutes.do(scheduled_task)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Start scheduler in background thread
scheduler_thread = Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

# Run initial collection
monitor.execute_lmstat()

# API Routes
@app.route('/api/status')
def get_status():
    """Get system status"""
    return jsonify({
        'last_update': monitor.last_update.isoformat() if monitor.last_update else None,
        'debug_mode': DEBUG_MODE,
        'update_interval_seconds': UPDATE_INTERVAL * 60,
        'health_status': monitor.health_status[-10:]  # Last 10 records
    })

@app.route('/api/health')
def get_health():
    """Get health status for visualization"""
    return jsonify(monitor.health_status)

@app.route('/api/licenses')
def get_licenses():
    """Get license data based on filter"""
    time_filter = request.args.get('filter', 'latest')
    data = monitor.get_aggregated_license_data(time_filter)
    if not data or not data.get('licenses'):
        return jsonify({'error': 'No data available for the selected period'}), 404
    
    return jsonify(data)

@app.route('/api/logs')
def get_logs():
    """Get log files list"""
    time_filter = request.args.get('filter', 'latest')
    files = monitor.get_log_files(time_filter)
    
    return jsonify({
        'files': files,
        'filter': time_filter
    })

@app.route('/api/logs/<filename>')
def get_log_content(filename):
    """Get specific log file content"""
    filepath = os.path.join(LOGS_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    licenses = monitor.parse_license_data(content)
    return jsonify({
        'filename': filename,
        'content': content,
        'licenses': licenses,
        'timestamp': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
    })

@app.route('/api/collect')
def manual_collect():
    """Manually trigger data collection"""
    success = monitor.execute_lmstat()
    return jsonify({
        'success': success,
        'timestamp': monitor.last_update.isoformat() if monitor.last_update else None
    })

@app.route('/api/users')
def get_user_statistics():
    """Get user-based statistics based on filter"""
    time_filter = request.args.get('filter', 'latest')
    
    if time_filter == 'latest':
        data = monitor.get_latest_license_data()
    else:
        data = monitor.get_aggregated_license_data(time_filter)

    if not data or not data.get('licenses'):
        return jsonify({'error': 'No data available for the selected period'}), 404
    
    user_stats = monitor.get_user_statistics(data['licenses'])
    
    return jsonify({
        'timestamp': data['timestamp'],
        'users': user_stats,
        'total_users': len(user_stats)
    })

@app.route('/api/modules')
def get_module_statistics():
    """Get module-based statistics based on filter"""
    time_filter = request.args.get('filter', 'latest')
    data = monitor.get_aggregated_license_data(time_filter)
    if not data or not data.get('licenses'):
        return jsonify({'error': 'No data available for the selected period'}), 404
    
    module_stats = monitor.get_module_statistics(data['licenses'])
    return jsonify({
        'timestamp': data['timestamp'],
        'modules': module_stats,
        'total_active_modules': len(module_stats)
    })

@app.route('/api/historical_summary')
def get_historical_summary_data():
    """Get historical summary data for charts."""
    time_filter = request.args.get('filter', 'week') # default to last week
    data = monitor.get_historical_summary(time_filter)
    return jsonify(data)

@app.route('/api/realtime_stats')
def get_realtime_stats():
    """Get latest user and license counts for real-time chart"""
    data = monitor.get_latest_license_data()
    if not data or not data.get('licenses'):
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'total_licenses_in_use': 0,
            'total_users': 0
        })

    licenses = data['licenses']
    total_licenses_in_use = sum(l.get('in_use', 0) for l in licenses)
    
    user_set = set()
    for license_data in licenses:
        for user in license_data.get('users', []):
            user_set.add(user['user'])
    total_users = len(user_set)

    return jsonify({
        'timestamp': data['timestamp'],
        'total_licenses_in_use': total_licenses_in_use,
        'total_users': total_users
    })

# Serve frontend
@app.route('/')
def serve_frontend():
    frontend_dir = resource_path('frontend')
    return send_from_directory(frontend_dir, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    frontend_dir = resource_path('frontend')
    return send_from_directory(frontend_dir, path)

if __name__ == '__main__':
    print(f"License Monitor starting...")
    print(f"Debug mode: {DEBUG_MODE}")
    print(f"Update interval: {UPDATE_INTERVAL} minutes")
    print(f"Logs directory: {LOGS_DIR}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)