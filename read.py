import json
import os
import time
from pathlib import Path

REQUEST_FILE = "read_request.txt"
RESPONSE_FILE = "read_response.txt"

# Directory containing the user JSON files.
SAVE_DIRECTORY = Path(".")


def parse_request(file_path):
    """Read key=value pairs from the request file."""
    request = {}

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if not line:
                    continue

                if "=" in line:
                    key, value = line.split("=", 1)
                    request[key.strip()] = value.strip()

    except OSError as error:
        print(f"Error reading request file: {error}")

    return request

#Response====================================================

def write_response(data):
    """Write a response dictionary to the response file."""
    try:
        with open(RESPONSE_FILE, "w", encoding="utf-8") as file:
            for key, value in data.items():

                # JSON-encode complex values so they can safely
                # travel through the text-file communication pipe.
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)

                file.write(f"{key}={value}\n")

    except OSError as error:
        print(f"Error writing response file: {error}")


def get_user_file_path(username, file_name):
    """
    Build the path to a user's JSON file.

    Example:
        username = "antonio"
        file_name = "games.json"

    Returns:
        antonio_games.json
    """

    # Prevent usernames or filenames from creating
    # directories outside SAVE_DIRECTORY.
    username = Path(username).name
    file_name = Path(file_name).name

    return SAVE_DIRECTORY / f"{username}_{file_name}"


def read_json_file(username, file_name):
    """
    Read a user's JSON file and return its contents.
    """

    path = get_user_file_path(username, file_name)

    if not path.exists():
        return {
            "status": "failure",
            "message": "File not found",
            "file_name": path.name
        }

    if not path.is_file():
        return {
            "status": "failure",
            "message": "Path is not a file",
            "file_name": path.name
        }

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return {
            "status": "success",
            "file_name": path.name,
            "data": data
        }

    except json.JSONDecodeError as error:
        return {
            "status": "failure",
            "message": f"Invalid JSON: {error}",
            "file_name": path.name
        }

    except OSError as error:
        return {
            "status": "failure",
            "message": f"Error reading file: {error}",
            "file_name": path.name
        }


def process_request():
    """Read and process one read request."""

    print("Read request found!")

    request = parse_request(REQUEST_FILE)
    print(request)

    command = request.get("command", "READ").upper()

    if command != "READ":
        response = {
            "status": "failure",
            "message": f"Unknown command: {command}"
        }

        write_response(response)
        return

    required_fields = (
        "username",
        "file_name"
    )

    if not all(field in request for field in required_fields):
        response = {
            "status": "failure",
            "message": "Missing username or file_name"
        }

        write_response(response)
        return

    username = request["username"]
    file_name = request["file_name"]

    if not file_name.lower().endswith(".json"):
        response = {
            "status": "failure",
            "message": "file_name must refer to a JSON file"
        }

        write_response(response)
        return

    response = read_json_file(
        username,
        file_name
    )

    write_response(response)

    print(response)


def main():
    """Run the Read microservice."""

    print("==============================")
    print(" Read Service Running")
    print("==============================")
    print("Watching for read_request.txt...")

    while True:

        if os.path.exists(REQUEST_FILE):

            try:
                process_request()

            except Exception as error:
                print(f"Unexpected error: {error}")

                write_response({
                    "status": "failure",
                    "message": str(error)
                })

            finally:
                # Remove the request so it is not processed again.
                try:
                    os.remove(REQUEST_FILE)

                except FileNotFoundError:
                    pass

        time.sleep(1)


if __name__ == "__main__":
    main()
