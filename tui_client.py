import aio_pika
import asyncio
import json
import curses
from collections import deque

log_data = deque(maxlen=100)  # Store up to 100 log entries

async def main(stdscr):
    # RabbitMQ connection
    connection = await aio_pika.connect_robust("amqp://localhost")
    channel = await connection.channel()

    # Declare the queue
    queue = await channel.declare_queue("", exclusive=True)

    async def callback(message):
        try:
            async with message.process():
                body = message.body.decode()
                level, name = message.routing_key.split(".")
                data = {"message": body, "level": level.upper(), "name": name}
                log_data.appendleft(data)  # Add the data to the global deque
                update_display(stdscr)
        except Exception as e:
            print(f"Error processing message: {e}")

    await queue.bind(exchange="topic_logs", routing_key="*.*")
    await queue.consume(callback)

    print("Waiting for logs. Press 'q' to quit.")
    try:
        while True:
            if await check_quit(stdscr):
                break
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        print("Stopping log consumer...")
    finally:
        await connection.close()

async def check_quit(stdscr):
    try:
        key = stdscr.getkey()
        return key.lower() == 'q'
    except curses.error:
        return False

def update_display(stdscr):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    
    for i, log in enumerate(log_data):
        if i >= height - 1:
            break
        log_line = f"{log['level']} - {log['name']}: {log['message']}"
        stdscr.addstr(i, 0, log_line[:width-1])
    
    stdscr.refresh()

def run_tui(stdscr):
    curses.curs_set(0)  # Hide the cursor
    stdscr.clear()
    stdscr.refresh()
    stdscr.nodelay(True)  # Set getch() to non-blocking
    
    asyncio.run(main(stdscr))

if __name__ == "__main__":
    curses.wrapper(run_tui)
