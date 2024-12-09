import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import socket
import threading
from datetime import datetime
import json
from pymongo import MongoClient

# HTTP-сервер
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.serve_file("index.html", "text/html")
        elif self.path == "/message.html":
            self.serve_file("message.html", "text/html")
        elif self.path == "/style.css":
            self.serve_file("style.css", "text/css")
        elif self.path == "/logo.png":
            self.serve_file("logo.png", "image/png")
        else:
            self.serve_file("error.html", "text/html", 404)

    def do_POST(self):
        if self.path == "/submit":
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)

                # Перевірка обов'язкових полів
                if "username" not in data or "message" not in data:
                    raise ValueError("Missing required fields")

                # Передаємо дані через сокет
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.sendto(json.dumps(data).encode(), ("127.0.0.1", 5000))

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "Message sent"}')
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(f"Error: {str(e)}".encode())
        else:
            self.serve_file("error.html", "text/html", 404)

    def serve_file(self, path, mime_type, status=200):
        try:
            with open(path, "rb") as f:
                self.send_response(status)
                self.send_header("Content-type", mime_type)
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

# Socket-сервер
def socket_server():
    client = MongoClient("mongodb://mongo:27017/")
    db = client['messages_db']
    collection = db['messages']

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 5000))
    print("Socket server is running on port 5000...")

    while True:
        data, _ = sock.recvfrom(4096)
        print(f"Received: {data.decode()}")
        message = json.loads(data.decode())
        document = {
            "date": datetime.now().isoformat(),
            "username": message["username"],
            "message": message["message"]
        }
        collection.insert_one(document)

# Запуск серверів
def run():
    http_thread = threading.Thread(target=lambda: HTTPServer(("0.0.0.0", 3000), SimpleHTTPRequestHandler).serve_forever())
    socket_thread = threading.Thread(target=socket_server)

    http_thread.start()
    socket_thread.start()

    http_thread.join()
    socket_thread.join()

if __name__ == "__main__":
    run()
