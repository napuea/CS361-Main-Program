import os
import time
from datetime import datetime

REQUEST_FILE = "reminder_request.txt"
RESPONSE_FILE = "reminder_response.txt"
CONFIG_FILE = "reminder_config.txt"

check_interval = 1


def load_alarm():

    if not os.path.exists(CONFIG_FILE):
        return None

    with open(CONFIG_FILE, "r") as f:
        return f.read().strip()


def save_alarm(alarm):

    with open(CONFIG_FILE, "w") as f:
        f.write(alarm)


def check_requests():

    if not os.path.exists(REQUEST_FILE):
        return

    with open(REQUEST_FILE, "r") as f:
        lines = [line.strip() for line in f.readlines()]

    if len(lines) == 0:
        return

    command = lines[0]

    if command == "SET_TIME" and len(lines) > 1:
        save_alarm(lines[1])

    elif command == "CLEAR":
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)

    open(REQUEST_FILE, "w").close()


def send_alert():

    with open(RESPONSE_FILE, "w") as f:
        f.write("ALERT\n")
        f.write("Time to start today's session!")


def main():
    already_sent = False
    while True:
        check_requests()
        alarm = load_alarm()
      
        if alarm:
            current = datetime.now().strftime("%H:%M")
            if current == alarm and not already_sent:
                send_alert()
                already_sent = True

            if current != alarm:
                already_sent = False

        time.sleep(check_interval)


if __name__ == "__main__":
    main()
  
