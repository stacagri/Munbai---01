from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"<h1>HELLO FROM VM! Connection Success!</h1>")
        print("RECEIVED GET REQUEST FROM:", self.client_address)

httpd = HTTPServer(('0.0.0.0', 8080), Handler)
print("Server listening on 8080...")
httpd.handle_request()
