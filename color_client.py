import pika
import json

# RabbitMQ connection
connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

# Declare the queue
result = channel.queue_declare("", exclusive=True)
queue_name = result.method.queue

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
def format(level, name, message):
    color = COLORS.get(level, RESET)
    body_color = (
        CRITICAL_BODY_COLOR
        if level == "CRITICAL"
        else BODY_COLOR
    )
    return f" {color} {level} {RESET} [{SECONDARY_COLOR}{name}{RESET}]: {body_color}{message}{RESET}"

def callback(ch, method, properties, body):
    try:
        log_message = body.decode("utf-8")
        level = method.routing_key.split(".")[0].upper()
        name = method.routing_key.split(".")[1]
        print(format(level, name, log_message))
    except Exception as e:
        print(f"Error processing message: {e}")


channel.queue_bind(exchange="topic_logs", queue=queue_name, routing_key="*.*")
channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

print("Waiting for logs. To exit press CTRL+C")
try:
    channel.start_consuming()
except KeyboardInterrupt:
    print("Stopping log consumer...")
finally:
    connection.close()
