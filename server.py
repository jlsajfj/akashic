import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import pika
from urllib.parse import urlparse, parse_qs
import cursor

# RabbitMQ connection parameters
RABBITMQ_HOST = "localhost"
RABBITMQ_EXCHANGE = "topic_logs"


class LoggingHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/log":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)

            try:
                log_data = json.loads(post_data.decode("utf-8"))
                self.process_log(log_data)
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Log received and processed")
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON data")
        else:
            self.send_error(404, "Endpoint not found")

    def process_log(self, log_data):
        level = log_data.get("level", "INFO")
        message = log_data.get("message")
        name = log_data.get("name", "default")

        if not message:
            raise ValueError("Message is required")

        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level not in valid_levels:
            level = "INFO"

        # Publish to RabbitMQ
        connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
        channel = connection.channel()

        channel.exchange_declare(exchange=RABBITMQ_EXCHANGE, exchange_type="topic")

        routing_key = f"{level.lower()}.{name}"
        channel.basic_publish(
            exchange=RABBITMQ_EXCHANGE,
            routing_key=routing_key,
            body=message,
        )

        connection.close()


def main():
    server_address = ("", 5231)
    httpd = HTTPServer(server_address, LoggingHandler)
    print(f"Server running on port 5231")
    log_data = {
        "level": "INFO",
        "message": "Server running on port 5231",
        "name": "akashic",
    }
    LoggingHandler.process_log(None, log_data)
    try:
        cursor.hide()
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped.")
        log_data = {"level": "INFO", "message": "Server stopped.", "name": "akashic"}
        LoggingHandler.process_log(None, log_data)
    except Exception as e:
        error_message = f"Critical server error: {str(e)}"
        log_data = {"level": "CRITICAL", "message": error_message, "name": "akashic"}
        LoggingHandler.process_log(None, log_data)
        print(error_message)
    finally:
        cursor.show()
        httpd.server_close()


if __name__ == "__main__":
    main()
