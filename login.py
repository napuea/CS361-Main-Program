import time
from pathlib import Path

REQUEST_FILE = Path("login_request.txt")
RESPONSE_FILE = Path("login_response.txt")
USERS_FILE = Path("users.txt")


def trim(value: str) -> str:
    return value.strip()


def parse_request(file_path: Path) -> dict[str, str]:
    data: dict[str, str] = {}

    try:
        with file_path.open("r", encoding="utf-8") as file:
            for line in file:
                position = line.find("=")

                if position != -1:
                    key = trim(line[:position])
                    value = trim(line[position + 1:])
                    data[key] = value
    except OSError:
        return {}

    return data


def validate_user(username: str, password: str) -> bool:
    try:
        with USERS_FILE.open("r", encoding="utf-8") as users:
            for line in users:
                colon = line.find(":")

                if colon != -1:
                    stored_user = trim(line[:colon])
                    stored_pass = trim(line[colon + 1:])

                    if stored_user == username and stored_pass == password:
                        return True
    except OSError:
        print("Error: Could not open users.txt.")

    return False


def write_response(status: str, message: str, username: str) -> None:
    try:
        with RESPONSE_FILE.open("w", encoding="utf-8") as response:
            response.write(f"status={status}\n")
            response.write(f"message={message}\n")

            if status == "success":
                response.write(f"username={username}\n")
    except OSError as error:
        print(f"Error: Could not create login_response.txt: {error}")

def print_file_contents(file_path: Path, label: str) -> None:
    """Print the contents of a text file in a readable format."""
    try:
        print(f"\n--- {label} ---")

        with file_path.open("r", encoding="utf-8") as file:
            contents = file.read()

        if contents.strip():
            print(contents.rstrip())
        else:
            print("(empty)")

        print(f"--- End {label} ---\n")

    except OSError as error:
        print(f"Could not read {file_path}: {error}")


def process_request() -> None:
    time.sleep(0.05)

    print("Login request found!")

    print_file_contents(
        REQUEST_FILE,
        "LOGIN REQUEST"
    )

    request = parse_request(REQUEST_FILE)

    try:
        REQUEST_FILE.unlink()
    except OSError as error:
        print(f"Warning: Failed to remove request file: {error}")

    username = request.get("username")
    password = request.get("password")

    if username is None or password is None:
        print("Invalid request format or file was empty.")

        write_response(
            "failure",
            "Invalid request format",
            ""
        )

        print_file_contents(
            RESPONSE_FILE,
            "LOGIN RESPONSE"
        )

        return

    if validate_user(username, password):
        write_response(
            "success",
            "Login successful",
            username
        )

        print(f"{username} logged in successfully.")

    else:
        write_response(
            "failure",
            "Invalid username or password",
            ""
        )

        print(f"Login failed for user: {username}")

    print_file_contents(
        RESPONSE_FILE,
        "LOGIN RESPONSE"
    )


def main() -> None:
    print("Login Service Running...")
    print("Watching for login_request.txt...")

    while True:
        if REQUEST_FILE.exists():
            process_request()

        time.sleep(0.1)


if __name__ == "__main__":
    main()
    
