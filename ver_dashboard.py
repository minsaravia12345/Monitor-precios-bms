import os
import http.server
import socketserver
import webbrowser
import threading
import time

PORT = 5050
directorio = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard", "public")
os.chdir(directorio)

Handler = http.server.SimpleHTTPRequestHandler

class MyServer(socketserver.TCPServer):
    allow_reuse_address = True

def run_server():
    try:
        with MyServer(("", PORT), Handler) as httpd:
            print(f"Sirviendo el Dashboard sin usar NodeJS en http://localhost:{PORT}/dashboard.html")
            httpd.serve_forever()
    except OSError as e:
        print(f"Error al iniciar el servidor (tal vez el puerto {PORT} esta en uso). Detalles: {e}")

# Iniciar servidor en hilo separado
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Esperar un segundo y abrir navegador
time.sleep(1)
webbrowser.open(f"http://localhost:{PORT}/dashboard.html")

print("\nPresiona CTRL+C para cerrar el dashboard y apagar el servidor.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nCerrando dashboard...")
