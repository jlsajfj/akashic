import http.server
import socketserver
import json
from urllib.parse import urlparse
import logging
import sys
import os
import cursor

# Define the path for akashic.log
AKASHIC_LOG = "/var/log/akashic.log"


class CustomFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[30m\033[102m",  # Black text on green background
        "INFO": "\033[30m\033[107m",  # Black text on white background
        "WARNING": "\033[30m\033[103m",  # Black text on yellow background
        "ERROR": "\033[97m\033[101m",  # White text on red background
        "CRITICAL": "\033[97m\033[41m",  # White text on red background
    }
    RESET = "\033[0m"
    SECONDARY_COLOR = "\033[94m"  # Light blue as secondary color
    BODY_COLOR = "\033[37m"  # White color for message body
    CRITICAL_BODY_COLOR = "\033[31m"  # Red color for critical message body

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        body_color = (
            self.CRITICAL_BODY_COLOR
            if record.levelname == "CRITICAL"
            else self.BODY_COLOR
        )
        return f" {color} {record.levelname} {self.RESET} [{self.SECONDARY_COLOR}{record.name}{self.RESET}]: {body_color}{record.getMessage()}{self.RESET}"


class DualHandler(logging.Handler):
    def __init__(self, file_path):
        super().__init__()
        self.setLevel(logging.DEBUG)  # Set the handler's level to DEBUG
        try:
            self.file_handler = logging.FileHandler(file_path)
            self.file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
                )
            )
            self.file_handler.setLevel(
                logging.DEBUG
            )  # Set file handler's level to DEBUG
        except PermissionError:
            print(
                f"Warning: Unable to write to {file_path}. Logs will only be printed to console."
            )
            self.file_handler = None
        self.stream_handler = logging.StreamHandler(sys.stdout)
        self.stream_handler.setFormatter(CustomFormatter())
        self.stream_handler.setLevel(
            logging.DEBUG
        )  # Set stream handler's level to DEBUG

    def emit(self, record):
        if self.file_handler:
            self.file_handler.emit(record)
        self.stream_handler.emit(record)


# Configure unified logging
akashic_handler = DualHandler(AKASHIC_LOG)


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Changed from INFO to DEBUG
    logger.addHandler(akashic_handler)
    return logger


# Get loggers
server_logger = get_logger("akashic")


class LoggingHandler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/post":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)

            try:
                data = json.loads(post_data.decode("utf-8"))
                level = data.get("level", "INFO").upper()
                message = data.get("message", "")
                name = data.get("name", "default")

                # Log the message using the named logger
                logger = get_logger(name)
                log_func = getattr(logger, level.lower(), logger.info)
                log_func(message)

                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b"Log received and processed")
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
    if akashic_handler.file_handler:
        server_logger.info(f"Logs will be written to {AKASHIC_LOG}")
    else:
        server_logger.warning(
            f"Unable to write logs to {AKASHIC_LOG}. Logs will only be printed to console."
        )

    with socketserver.TCPServer(("localhost", PORT), Handler) as httpd:
        print(f"Serving at port {PORT}")
        if akashic_handler.file_handler:
            print(f"Logs will be written to {AKASHIC_LOG}")
        else:
            print(
                f"Unable to write logs to {AKASHIC_LOG}. Logs will only be printed to console."
            )
        try:
            cursor.hide()
            httpd.serve_forever()
        except KeyboardInterrupt:
            server_logger.info("Server stopped.")
        finally:
            cursor.show()
            httpd.server_close()
