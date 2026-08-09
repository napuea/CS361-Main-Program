import os
import time
import mimetypes
from pathlib import Path
from datetime import datetime

REQUEST_FILE = "read_request.txt"
RESPONSE_FILE = "read_response.txt"

# Change this to your media library location
SEARCH_DIRECTORY = "."


def parse_request(filepath):
    request = {}
    with open(filepath, "r") as file:
        for line in file:
            line = line.strip()
            if "=" in line:
                key, value = line.split("=", 1)
                request[key] = value

    return request


def determine_media_type(path):
    mime, _ = mimetypes.guess_type(path)

    if mime is None:
        return "other"

    if mime.startswith("image"):
        return "image"

    if mime.startswith("video"):
        return "video"

    if mime.startswith("audio"):
        return "audio"

    if mime.startswith("text"):
        return "text"

    if mime == "application/pdf":
        return "pdf"

    if "zip" in mime:
        return "archive"

    return "other"


def get_metadata(filename):
    path = Path(filename)

    if not path.exists():
        return {
            "status": "failure",
            "message": "File not found"
        }

    stats = path.stat()

    return {
        "status": "success",
        "file_name": path.name,
        "file_path": str(path.resolve()),
        "file_type": path.suffix.lower(),
        "media_type":
            determine_media_type(path),
        "file_size":
            stats.st_size,
        "modified":
            datetime.fromtimestamp(
                stats.st_mtime
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
    }


def search_files(keyword):
    results = []

    keyword = keyword.lower()
    root = Path(SEARCH_DIRECTORY)

    for file in root.rglob("*"):
        if file.is_file():
            if keyword in file.name.lower():
                metadata = get_metadata(file)
                results.append(metadata)

    return results


def write_response(data):
    with open(RESPONSE_FILE, "w") as file:
        for key, value in data.items():
            file.write(
                f"{key}={value}\n"
            )


def build_search_response(results):
    response = {"status": "success", "results": len(results)}

    index = 1

    for item in results:
        response[f"file{index}_name"] = (
            item["file_name"]
        )
        response[f"file{index}_path"] = (
            item["file_path"]
        )
        response[f"file{index}_type"] = (
            item["file_type"]
        )
        response[f"file{index}_media"] = (
            item["media_type"]
        )
        response[f"file{index}_size"] = (
            item["file_size"]
        )
        index += 1

    return response


def main():
    print("==============================")
    print(" Read Service Running")
    print("==============================")

    while True:
        if os.path.exists(REQUEST_FILE):
            print("Request received")
            try:
                request = parse_request(
                    REQUEST_FILE
                )
                command = request.get(
                    "command",
                    "READ"
                ).upper()


                if command == "READ":
                    if "file_name" in request:
                        response = get_metadata(
                            request["file_name"]
                        )
                    else:
                        response = {
                            "status": "failure",
                            "message":
                                "Missing file_name"
                        }


                elif command == "SEARCH":
                    if "keyword" in request:
                        results = search_files(
                            request["keyword"]
                        )
                        response = (
                            build_search_response(
                                results
                            )
                        )
                    else:
                        response = {
                            "status": "failure",
                            "message":
                                "Missing keyword"
                        }


                else:
                    # If command is invalid
                    response = {
                        "status": "failure",
                        "message":
                            "Unknown command"
                    }

                write_response(response)

            except Exception as e:
                write_response({
                    "status": "failure",
                    "message": str(e)
                })

            finally:
                try:
                    os.remove(REQUEST_FILE)
                except FileNotFoundError:
                    pass
        time.sleep(1)


if __name__ == "__main__":
    main()
  
