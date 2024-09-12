import aio_pika
import asyncio
import json
import curses
from collections import deque
import datetime

LOG_LEVELS = ["Critical", "Error", "Warning", "Info", "Debug", "All"]
log_data = {level.lower(): deque(maxlen=500) for level in LOG_LEVELS}
names = ["All"]
selected_level = 5
selected_name = 0


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
                if name not in names:
                    names.append(name)
                timestamp = message.timestamp.astimezone(
                    datetime.timezone(datetime.timedelta(hours=-4))
                ).strftime("%H:%M:%S")
                data = {
                    "message": body,
                    "level": level.upper(),
                    "name": name,
                    "timestamp": timestamp,
                }
                log_data["all"].appendleft(data)
                log_data[level].appendleft(data)
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
    global selected_level, selected_name, max_name_index
    try:
        key = stdscr.getkey()
        if key.lower() == "q":
            return True
        elif key == "KEY_UP":
            selected_level = max(0, selected_level - 1)
            update_display(stdscr)
        elif key == "KEY_DOWN":
            selected_level = min(5, selected_level + 1)
            update_display(stdscr)
        elif key == "KEY_LEFT":
            selected_name = max(0, selected_name - 1)
            update_display(stdscr)
        elif key == "KEY_RIGHT":
            selected_name = min(len(names) - 1, selected_name + 1)
            update_display(stdscr)
        return False
    except curses.error:
        return False


def update_display(stdscr):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    stdscr.addstr(0, width // 2 - 6, "akashic logs")

    data = log_data[LOG_LEVELS[selected_level].lower()]

    if selected_name != 0:
        data = [d for d in data if d["name"] == names[selected_name]]

    for i, log in enumerate(data):
        if i >= height - 2:
            break

        secondary_color = curses.color_pair(1)
        level = log["level"]
        if level == "CRITICAL":
            color_pair = curses.color_pair(2)
            secondary_color = curses.color_pair(2)
        elif level == "ERROR":
            color_pair = curses.color_pair(2)
        elif level == "WARNING":
            color_pair = curses.color_pair(3)
        elif level == "INFO":
            color_pair = curses.color_pair(1)
        else:
            color_pair = curses.color_pair(4)

        y = i + 1

        timestamp = log["timestamp"]
        log_line = f" {log['level']:<9} {log['name']:<10} {log['message']}"
        stdscr.addstr(y, 0, " " + timestamp, curses.color_pair(6))
        stdscr.addstr(
            y,
            len(timestamp) + 1,
            " {:<9}".format(log["level"]),
            color_pair,
        )
        formatted_name = "{:<10} ".format(log["name"])
        stdscr.addstr(y, len(timestamp) + 11, formatted_name, curses.color_pair(5))
        stdscr.addstr(
            y,
            len(timestamp) + 12 + len(formatted_name),
            log["message"],
            secondary_color,
        )

    for i, level in enumerate(LOG_LEVELS):
        y = height - len(LOG_LEVELS) + i - 1
        stdscr.addstr(y, width - 10, " ")
        if i == selected_level:
            stdscr.addstr(y, width - 9, level, curses.A_REVERSE)
        else:
            stdscr.addstr(y, width - 9, level)
        stdscr.addstr(y, width - 9 + len(level), " " * (9 - len(level)))

    stdscr.addstr(height - 1, 0, " " * (width - 1))
    cur_len = 1
    for i, name in enumerate(names):
        if i == selected_name:
            stdscr.addstr(height - 1, cur_len, name, curses.A_REVERSE)
        else:
            stdscr.addstr(height - 1, cur_len, name)
        cur_len += len(name) + 1

    stdscr.refresh()


def run_tui(stdscr):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_GREEN, -1)
    curses.init_pair(5, curses.COLOR_BLUE, -1)
    curses.init_pair(6, curses.COLOR_CYAN, -1)
    stdscr.clear()
    stdscr.refresh()
    stdscr.nodelay(True)

    asyncio.run(main(stdscr))


if __name__ == "__main__":
    curses.wrapper(run_tui)
