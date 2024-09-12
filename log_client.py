import pika
import json

AKASHIC_LOG = "/var/log/akashic.log"

# RabbitMQ connection
connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

# Declare the queue
result = channel.queue_declare("", exclusive=True)
queue_name = result.method.queue


def callback(ch, method, properties, body):
    try:
        log_message = body.decode("utf-8")
        routing_key = method.routing_key
        level, name = routing_key.split(".")
        timestamp = properties.timestamp
        with open(AKASHIC_LOG, "a") as f:
            print(f"{timestamp} - {level} - {name} - {log_message}", file=f)
        print(f" [{timestamp}] {routing_key}")
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
