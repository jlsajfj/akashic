import http.server
import socketserver
import json
from urllib.parse import urlparse
import logging
import sys


# Configure logging for received logs
class DualHandler(logging.Handler):
    def __init__(self, file_path):
        super().__init__()
        self.file_handler = logging.FileHandler(file_path)
        self.stream_handler = logging.StreamHandler(sys.stdout)

    def emit(self, record):
        self.file_handler.emit(record)
        self.stream_handler.emit(record)


akashic_logger = logging.getLogger("akashic")
akashic_logger.setLevel(logging.INFO)
dual_handler = DualHandler("akashic.log")
dual_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
akashic_logger.addHandler(dual_handler)

# Configure logging for server operations
server_logger = logging.getLogger("server")
server_logger.setLevel(logging.INFO)
server_handler = logging.FileHandler("server.log")
server_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
server_logger.addHandler(server_handler)
server_logger.addHandler(logging.StreamHandler(sys.stdout))


class LoggingHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/post":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)

            try:
                data = json.loads(post_data.decode("utf-8"))
                level = data.get("level", "INFO")
                message = data.get("message", "")

                # Log the message using akashic_logger
                log_func = getattr(akashic_logger, level.lower(), akashic_logger.info)
                log_func(f"{message}")

                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Log received and processed")

                # Log the successful operation using server_logger
                server_logger.info(f"Processed log: level={level}, message={message}")
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON data")
                server_logger.error("Received invalid JSON data")
        else:
            self.send_error(404, "Endpoint not found")
            server_logger.warning(
                f"Attempted access to non-existent endpoint: {self.path}"
            )

    def log_message(self, format, *args):
        # Use server_logger for server operation logs
        server_logger.info(format % args)


if __name__ == "__main__":
    PORT = 5231
    Handler = LoggingHandler

    server_logger.info(f"Starting server on localhost:{PORT}")
    with socketserver.TCPServer(("localhost", PORT), Handler) as httpd:
        print(f"Serving at port {PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            server_logger.info("Server stopped.")
        finally:
            httpd.server_close()
