import requests
import json


def send_log(name, level, message):
    url = "http://localhost:5231/post"
    headers = {"Content-Type": "application/json"}
    data = {"name": name, "level": level, "message": message}
    response = requests.post(url, headers=headers, json=data)
    return response.status_code


def main():
    log_levels = ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"]

    for level in log_levels:
        status_code = send_log("MyApp", level, "Test log message")
        print(f"Log sent with level {level}. Status code: {status_code}")


if __name__ == "__main__":
    main()
