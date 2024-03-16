import http.server
import socketserver
import telebot
import handlers
from config import bot

PORT = 80


class LocalServer(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        # Handle POST requests
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        post_data_str = post_data.decode('utf-8')
        update = telebot.types.Update.de_json(post_data_str)

        # Process the update with the bot
        bot.process_new_updates([update])

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        response = b"Received POST request with data: " + post_data
        self.wfile.write(response)


if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), LocalServer) as httpd:
        print(f"Server started on port {PORT}")
        httpd.serve_forever()
