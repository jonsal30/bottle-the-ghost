#!/usr/bin/env python3
import http.server, os, pathlib, socketserver, threading, webbrowser
PORT=int(os.environ.get('CIAB_PORT','8765')); HOST='127.0.0.1'; ROOT=pathlib.Path(__file__).resolve().parent; os.chdir(ROOT)
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self,fmt,*args):pass
    def end_headers(self):
        self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','no-referrer'); self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'none'; frame-src 'none'; object-src 'none'"); super().end_headers()
class S(socketserver.TCPServer): allow_reuse_address=True
def open_browser():
    import time; time.sleep(.5); webbrowser.open(f'http://{HOST}:{PORT}/lab_dashboard.html?godmode=1')
print(f'🖤 Cloud in a Bottle — http://{HOST}:{PORT}/lab_dashboard.html?godmode=1'); print(f'🗺️ Offline map — http://{HOST}:{PORT}/map.html?godmode=1'); print('🔒 Bound to loopback only.')
threading.Thread(target=open_browser,daemon=True).start()
with S((HOST,PORT),H) as httpd:
    try:httpd.serve_forever()
    except KeyboardInterrupt:print('\nClosed')