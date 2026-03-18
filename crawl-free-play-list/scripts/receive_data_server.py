#!/usr/bin/env python3
"""Simple HTTP server to receive JSON data from browser."""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

received_data = {}

class DataHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        data = json.loads(body.decode('utf-8'))
        
        filename = data.get('filename', 'unknown')
        items = data.get('items', [])
        
        # Security: only allow safe filenames (alphanumeric, underscore, dash, dot)
        if not re.match(r'^[a-zA-Z0-9_\-]+\.json$', filename):
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid filename'}).encode())
            return
        
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        
        print(f"Saved {len(items)} items to {filepath}")
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'ok': True, 'count': len(items)}).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        print(f"[Server] {format % args}")

server = HTTPServer(('127.0.0.1', 18765), DataHandler)
print(f"Data directory: {DATA_DIR}")
print("Server listening on http://127.0.0.1:18765")
print("Waiting for data...")
sys.stdout.flush()
server.serve_forever()
