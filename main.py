import mimetypes
import socket
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, unquote_plus
from http.server import HTTPServer, BaseHTTPRequestHandler
from multiprocessing import Process
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# Налаштування логування
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Словник для маршрутизації
routes = {
    "/": "index.html",
    "/message": "message.html"
}

class HttpHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        size = int(self.headers["Content-Length"])
        data = self.rfile.read(size)

        try:
            # Відправка даних через UDP-сокет
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
                client_socket.sendto(data, ("127.0.0.1", 5000))
        except socket.error as e:
            print(f"Failed to send data: {e}")

        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()

    def do_GET(self):
        router = urlparse(self.path).path
        # Обробка маршрутів
        if router in routes:
            self.send_file(routes[router])
        elif Path(__file__).parent.joinpath(router[1:]).exists():
            self.send_static()
        else:
            self.send_file("error.html", "text/html", 404)

    def send_file(self, filename, mimetype="text/html", status=200):
        self.send_response(status)
        self.send_header("Content-type", mimetype)
        self.end_headers()
        with open(filename, 'rb') as file:
            self.wfile.write(file.read())

    def send_static(self):
        mimetype = mimetypes.guess_type(self.path)[0] or "text/plain"
        self.send_file(f".{self.path}", mimetype)

def save_to_db(data):
    # Підключення до MongoDB
    client = MongoClient("mongodb://mongodb:27017", server_api=ServerApi('1'))
    db = client.project
    try:
        data = unquote_plus(data)
        parse_data = dict([i.split("=") for i in data.split("&")])
        parse_data["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.messages.insert_one(parse_data)
    except Exception as e:
        print(f"Error saving to DB: {e}")
    finally:
        client.close()

def run_socket_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 5000))
    print(f"Socket server started at socket://127.0.0.1:5000")
    try:
        while True:
            data, addr = s.recvfrom(1024)
            print(f"Received from {addr}: {data.decode()}")
            save_to_db(data.decode())
    except Exception as e:
        print(f"Error in socket server: {e}")
    finally:
        s.close()

def run_http_server():
    server_address = ("0.0.0.0", 3000)
    http = HTTPServer(server_address, HttpHandler)
    print(f"HTTP server started at http://0.0.0.0:3000")
    try:
        http.serve_forever()
    except Exception as e:
        print(f"Error in HTTP server: {e}")
    finally:
        print("HTTP server stopped")

if __name__ == '__main__':
    # Запуск серверів у різних процесах
    http_server_process = Process(target=run_http_server, name="HTTP_Server")
    socket_server_process = Process(target=run_socket_server, name="SOCKET_Server")

    http_server_process.start()
    socket_server_process.start()

    http_server_process.join()
    socket_server_process.join()

