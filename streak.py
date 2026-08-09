import json
import os
import time
from datetime import date, datetime

REQUEST_FILE = "session_request.txt"
RESPONSE_FILE = "session_response.txt"
DATABASE_FILE = "session_db.json"


def load_database():
    if not os.path.exists(DATABASE_FILE):
        return {}

    with open(DATABASE_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_database(db):
    with open(DATABASE_FILE, "w") as f:
        json.dump(db, f, indent=4)


def read_request():
    if not os.path.exists(REQUEST_FILE):
        return None

    with open(REQUEST_FILE, "r") as f:
        lines = f.readlines()

    if not lines:
        return None

    request = {}

    for line in lines:
        if "=" in line:
            key, value = line.strip().split("=", 1)
            request[key] = value

    return request


def clear_request():
    with open(REQUEST_FILE, "w"):
        pass


def write_response(data):
    with open(RESPONSE_FILE, "w") as f:
        for key, value in data.items():
            f.write(f"{key}={value}\n")


def start_session(db, username):
    today = date.today()

    if username not in db:
        db[username] = {
            "last_session": str(today),
            "streak": 1
        }

    else:
        last = datetime.strptime(
            db[username]["last_session"],
            "%Y-%m-%d"
        ).date()

        difference = (today - last).days

        if difference == 0:
            # Already started today
            pass

        elif difference == 1:
            db[username]["streak"] += 1
            db[username]["last_session"] = str(today)

        else:
            db[username]["streak"] = 1
            db[username]["last_session"] = str(today)

    save_database(db)

    return {
        "status": "SUCCESS",
        "user": username,
        "current_streak": db[username]["streak"],
        "last_session": db[username]["last_session"]
    }


def get_streak(db, username):

    if username not in db:
        return {
            "status": "NOT_FOUND"
        }

    return {
        "status": "SUCCESS",
        "user": username,
        "current_streak": db[username]["streak"],
        "last_session": db[username]["last_session"]
    }


def process_request(request):

    db = load_database()

    command = request.get("command", "")
    username = request.get("user", "")

    if command == "START_SESSION":
        response = start_session(db, username)

    elif command == "GET_STREAK":
        response = get_streak(db, username)

    else:
        response = {
            "status": "UNKNOWN_COMMAND"
        }

    write_response(response)


def main():

    print("Session Service Running...")

    while True:

        request = read_request()

        if request:
            process_request(request)
            clear_request()

        time.sleep(0.5)


if __name__ == "__main__":
    main()
  
