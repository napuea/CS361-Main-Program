import os
import time
from datetime import datetime

REQUEST_FILE = "reminder_request.txt"
RESPONSE_FILE = "reminder_response.txt"
CONFIG_FILE = "reminder_config.txt"

CHECK_INTERVAL = 1


def print_file_contents(file_path, label):
    """Print the contents of a text file in a readable format."""
    try:
        print(f"\n--- {label} ---")

        with open(file_path, "r", encoding="utf-8") as file:
            contents = file.read()

        if contents.strip():
            print(contents.rstrip())
        else:
            print("(empty)")

        print(f"--- End {label} ---\n")

    except OSError as error:
        print(f"Could not read {file_path}: {error}")


def load_alarm():
    """Load the configured alarm time."""
    if not os.path.exists(CONFIG_FILE):
        return None

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            alarm = file.read().strip()

        if not alarm:
            return None

        return alarm

    except OSError:
        return None


def save_alarm(alarm):
    """Save the configured alarm time."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        file.write(alarm)


def clear_request_file():
    """Clear the reminder request file."""
    try:
        with open(REQUEST_FILE, "w", encoding="utf-8"):
            pass

    except OSError as error:
        print(f"Could not clear request file: {error}")


def check_requests():
    """Process commands from reminder_request.txt."""
    if not os.path.exists(REQUEST_FILE):
        return

    try:
        with open(REQUEST_FILE, "r", encoding="utf-8") as file:
            lines = [
                line.strip()
                for line in file
                if line.strip()
            ]

    except OSError as error:
        print(f"Could not read request file: {error}")
        return

    if not lines:
        return

    # Print the actual request file contents.
    print_file_contents(
        REQUEST_FILE,
        "REMINDER REQUEST"
    )

    command = lines[0]

    if command == "SET_TIME":
        if len(lines) > 1:
            alarm = lines[1]

            try:
                datetime.strptime(alarm, "%H:%M")
                save_alarm(alarm)

                print(f"Alarm set for {alarm}")

            except ValueError:
                print(f"Invalid alarm time: {alarm}")

    elif command == "CLEAR":
        if os.path.exists(CONFIG_FILE):
            try:
                os.remove(CONFIG_FILE)
                print("Today's alarm cleared.")

            except OSError as error:
                print(f"Could not clear alarm: {error}")

        else:
            print("No alarm was configured.")

    else:
        print(f"Unknown reminder command: {command}")

    clear_request_file()


def send_alert():
    """Send an alert to the main application."""
    try:
        with open(RESPONSE_FILE, "w", encoding="utf-8") as file:
            file.write("ALERT\n")
            file.write("Time to start today's session!\n")

        print("Reminder alert sent.")

        # Print the actual response file contents.
        print_file_contents(
            RESPONSE_FILE,
            "REMINDER RESPONSE"
        )

    except OSError as error:
        print(f"Could not write reminder response: {error}")


def main():
    """Run the reminder microservice."""
    print("Reminder Service Running...")
    print("Watching for reminder requests...")

    last_alert_time = None

    while True:
        check_requests()

        alarm = load_alarm()

        if alarm:
            try:
                alarm_time = datetime.strptime(
                    alarm,
                    "%H:%M"
                ).time()

                current_datetime = datetime.now()
                current_time = current_datetime.time()

                current_minute = current_datetime.strftime(
                    "%H:%M"
                )

                if current_time.hour == alarm_time.hour:
                    if current_time.minute == alarm_time.minute:
                        if last_alert_time != current_minute:
                            send_alert()
                            last_alert_time = current_minute

            except ValueError:
                print(
                    f"Invalid alarm configuration: {alarm}"
                )

        else:
            last_alert_time = None

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
