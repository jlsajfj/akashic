import pika
import json

# RabbitMQ connection
connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

# Declare the queue
result = channel.queue_declare("", exclusive=True)
queue_name = result.method.queue


def callback(ch, method, properties, body):
    try:
        log_message = body.decode("utf-8")
        level = method.routing_key.split(".")[0]
        name = method.routing_key.split(".")[1]
        print(f"[{level}] [{name}] {log_message}")
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
