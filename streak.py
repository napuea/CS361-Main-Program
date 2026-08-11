import json
import os
import time
from pathlib import Path

REQUEST_FILE = "save_request.txt"
RESPONSE_FILE = "save_response.txt"

# Directory where the user JSON files are stored.
# "." means the same directory as save.py.
SAVE_DIRECTORY = Path(".")


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


def parse_request(file_path):
    """Read key=value pairs from the save request file."""
    data = {}

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if not line:
                    continue

                position = line.find("=")

                if position != -1:
                    key = line[:position].strip()
                    value = line[position + 1:].strip()

                    data[key] = value

    except OSError as error:
        print(f"Error reading request file: {error}")

    return data


def write_response(status, file_name="", error_message=""):
    """Write the result of the save operation."""
    try:
        with open(RESPONSE_FILE, "w", encoding="utf-8") as response:
            response.write(f"status={status}\n")

            if file_name:
                response.write(f"file_saved={file_name}\n")

            if error_message:
                response.write(f"error={error_message}\n")

        # Print the actual response file after writing it.
        print_file_contents(
            RESPONSE_FILE,
            "SAVE RESPONSE"
        )

    except OSError as error:
        print(f"Error writing response file: {error}")


def get_user_file_path(username, file_name):
    """
    Build the path to a user's JSON file.

    Example:
        username = "antonio"
        file_name = "games.json"

    Results in:
        antonio_games.json
    """

    # Prevent directory traversal through the username or filename.
    username = Path(username).name
    file_name = Path(file_name).name

    return SAVE_DIRECTORY / f"{username}_{file_name}"


def validate_json_data(data):
    """
    Verify that the supplied string contains valid JSON.

    Returns:
        True  - valid JSON
        False - invalid JSON
    """
    try:
        json.loads(data)
        return True

    except json.JSONDecodeError as error:
        print(f"Invalid JSON data: {error}")
        return False


def save_json_file(username, file_name, data):
    """
    Save complete JSON data to the user's JSON file.

    The data received from the client is expected to already
    be a JSON string.
    """

    path = get_user_file_path(username, file_name)

    # Make sure the data is actually valid JSON before
    # overwriting the user's existing file.
    try:
        json_data = json.loads(data)

    except json.JSONDecodeError as error:
        print(f"Cannot save invalid JSON: {error}")
        return False

    try:
        with open(path, "w", encoding="utf-8") as save_file:
            json.dump(
                json_data,
                save_file,
                indent=4
            )

            save_file.write("\n")

        return True

    except OSError as error:
        print(f"Error saving JSON file: {error}")
        return False


def process_request():
    """Read and process one save request."""

    print("Save request found!")

    # Print the actual request file before processing it.
    print_file_contents(
        REQUEST_FILE,
        "SAVE REQUEST"
    )

    request = parse_request(REQUEST_FILE)

    required_fields = (
        "username",
        "file_name",
        "save_data"
    )

    if not all(field in request for field in required_fields):
        print("Invalid request: missing required field.")

        write_response(
            "failure",
            error_message="Missing required field."
        )

        return

    username = request["username"]
    file_name = request["file_name"]
    save_data = request["save_data"]

    # Make sure the filename is a JSON file.
    if not file_name.lower().endswith(".json"):
        print("Invalid request: file must be a JSON file.")

        write_response(
            "failure",
            error_message="file_name must refer to a JSON file."
        )

        return

    # Save the JSON.
    if save_json_file(
        username,
        file_name,
        save_data
    ):
        user_file_name = get_user_file_path(
            username,
            file_name
        ).name

        write_response(
            "success",
            user_file_name
        )

        print(f"Saved: {user_file_name}")

    else:
        write_response(
            "failure",
            error_message="Could not save JSON data."
        )


def main():
    """Run the Save microservice."""

    print("Save Service Running...")
    print("Watching for save_request.txt...")

    while True:

        if os.path.exists(REQUEST_FILE):

            try:
                process_request()

            except Exception as error:
                print(f"Unexpected error: {error}")

                write_response(
                    "failure",
                    error_message=str(error)
                )

            finally:
                # Remove the request so it is not processed again.
                try:
                    os.remove(REQUEST_FILE)

                except FileNotFoundError:
                    pass

        # Check for another request every second.
        time.sleep(1)


if __name__ == "__main__":
    main()
