from __future__ import annotations

import json
import re
import time
import uuid
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Any, Callable, Optional

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


# ---------------------------------------------------------------------------
# Paths / configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "assets"
SERVICE_DIR = BASE_DIR

LOGIN_REQUEST = SERVICE_DIR / "login_request.txt"
LOGIN_RESPONSE = SERVICE_DIR / "login_response.txt"

READ_REQUEST = SERVICE_DIR / "read_request.txt"
READ_RESPONSE = SERVICE_DIR / "read_response.txt"

SAVE_REQUEST = SERVICE_DIR / "save_request.txt"
SAVE_RESPONSE = SERVICE_DIR / "save_response.txt"

REMINDER_REQUEST = SERVICE_DIR / "reminder_request.txt"
REMINDER_RESPONSE = SERVICE_DIR / "reminder_response.txt"

STREAK_REQUEST = SERVICE_DIR / "session_request.txt"
STREAK_RESPONSE = SERVICE_DIR / "session_response.txt"

SERVICE_POLL_MS = 100
SERVICE_TIMEOUT_MS = 5000
TIMER_UPDATE_MS = 1000
REMINDER_POLL_MS = 500

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

PANEL = "#9dbbea"
PANEL_DARK = "#3974c9"
BLUE = "#1859c9"
TAB_BLUE = "#a8c3ef"
GREEN = "#6aac4e"
YELLOW = "#ffe49b"
RED = "#df6666"
WHITE = "#f2f2f2"
BLACK = "#111111"
BORDER = "#3d3d3d"

# ---------------------------------------------------------------------------
# Game data
# ---------------------------------------------------------------------------

# Each user has a separate JSON file managed by read.py/save.py.
GAME_DATA_FILE = "games.json"


# ---------------------------------------------------------------------------
# Formatting / parsing helpers
# ---------------------------------------------------------------------------

def fmt_time(minutes: float | int) -> str:
    total_minutes = max(0, int(minutes))
    hours, mins = divmod(total_minutes, 60)
    return f"{hours}h{mins:02d}m" if hours else f"0h{mins:02d}m"


def fmt_duration(seconds: float) -> str:
    total_ms = max(0, int(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def parse_key_value_response(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data

    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                data[key.strip()] = value.strip()
    except OSError:
        return {}

    return data


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_game(game: dict[str, Any]) -> dict[str, Any]:
    result = dict(game)
    result["title"] = str(result.get("title", "Untitled"))
    result["playtime"] = max(0.0, float(result.get("playtime", 0) or 0))
    result["status"] = str(result.get("status", "Collection"))
    result["cover"] = result.get("cover")
    result["estimated"] = str(result.get("estimated", "Unknown"))
    result["sessions"] = max(0, safe_int(result.get("sessions", 0)))
    result["started"] = str(result.get("started", ""))
    result["review"] = str(result.get("review", ""))
    result["days_paused"] = max(0, safe_int(result.get("days_paused", 0)))
    return result


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class GameThroughApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("GAMETHROUGH")
        self.geometry("1200x675")
        self.minsize(1000, 620)
        self.configure(bg=PANEL)

        # Game data is loaded from the logged-in user's JSON file
        # through the Read microservice after authentication.
        self.games: list[dict[str, Any]] = []

        self.current_page = "login"
        self.username: Optional[str] = None

        self.username_entry: Optional[tk.Entry] = None
        self.password_entry: Optional[tk.Entry] = None
        self.login_status: Optional[tk.Label] = None

        self.streak_label: Optional[tk.Label] = None
        self.search_entry: Optional[tk.Entry] = None

        self.login_pending = False
        self.data_loading = False
        self.closing = False

        self.service_queue: list[tuple[
            Path, Path, list[str], Callable[[dict[str, str]], None], int
        ]] = []
        self.service_busy = False
        self.service_request_id: Optional[str] = None

        self.search_var = tk.StringVar()

        self.timer_game: Optional[dict[str, Any]] = None
        self.timer_running = False
        self.timer_started_at = 0.0
        self.timer_job: Optional[str] = None
        self.timer_controls: list[tuple[dict[str, Any], tk.Button, Optional[tk.Label]]] = []

        self.cover_cache: dict[tuple[str, int, int], Any] = {}
        self.bg_image = None
        self.bg_photo = None

        self.root_container = tk.Frame(self, bg=PANEL)
        self.root_container.pack(fill="both", expand=True)

        self._load_background()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.poll_reminder_response()
        self.show_login()

    # ------------------------------------------------------------------
    # Visual helpers
    # ------------------------------------------------------------------

    def _load_background(self) -> None:
        if Image is None:
            return

        path = ASSET_DIR / "background.jpeg"
        if not path.exists():
            return

        try:
            with Image.open(path) as source:
                self.bg_image = source.convert("RGB")
        except OSError:
            self.bg_image = None

    def _draw_background(self, parent: tk.Frame) -> None:
        if Image is None or self.bg_image is None:
            parent.configure(bg="#1d1a19")
            return

        width = max(parent.winfo_width(), 1200)
        height = max(parent.winfo_height(), 675)

        image = self.bg_image.resize((width, height))
        self.bg_photo = ImageTk.PhotoImage(image)

        label = tk.Label(parent, image=self.bg_photo, bd=0)
        label.place(x=0, y=0, relwidth=1, relheight=1)

    def clear(self) -> None:
        for child in self.root_container.winfo_children():
            child.destroy()

        self.search_entry = None
        self.streak_label = None
        self.timer_controls = []

    @staticmethod
    def title_label(parent: tk.Misc, text: str = "GAMETHROUGH") -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            font=("Arial", 32, "bold"),
            fg="white",
            bg="#151313",
        )

    @staticmethod
    def make_button(
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
        bg: Optional[str] = None,
        fg: Optional[str] = None,
        font: Optional[tuple[str, int]] = None,
        width: Optional[int] = None,
    ) -> tk.Button:
        bg = bg or WHITE
        fg = fg or BLACK
        font = font or ("Arial", 15)

        options: dict[str, Any] = {
            "text": text,
            "command": command,
            "bg": bg,
            "fg": fg,
            "activebackground": bg,
            "activeforeground": fg,
            "relief": "solid",
            "bd": 1,
            "font": font,
            "cursor": "hand2",
        }

        if width is not None:
            options["width"] = width

        return tk.Button(parent, **options)

    @staticmethod
    def card(parent: tk.Misc, **kwargs: Any) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=PANEL_DARK,
            highlightbackground=BORDER,
            highlightthickness=1,
            **kwargs,
        )

    @staticmethod
    def format_title(title: str, max_len: int = 25) -> str:
        return title if len(title) <= max_len else title[: max_len - 1] + "…"

    # ------------------------------------------------------------------
    # Text-file IPC
    # ------------------------------------------------------------------

    @staticmethod
    def _clear_service_files(request_file: Path, response_file: Path) -> None:
        for path in (request_file, response_file):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass

    @staticmethod
    def _atomic_write(path: Path, text: str) -> None:
        temp = path.with_name(
            f".{path.name}.{uuid.uuid4().hex}.tmp"
        )

        try:
            temp.write_text(text, encoding="utf-8")
            temp.replace(path)
        finally:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass

    def _send_service_request(
        self,
        request_file: Path,
        response_file: Path,
        lines: list[str],
        callback: Callable[[dict[str, str]], None],
        timeout: int = SERVICE_TIMEOUT_MS,
    ) -> None:
        self.service_queue.append(
            (request_file, response_file, lines, callback, timeout)
        )
        self._process_service_queue()

    def _process_service_queue(self) -> None:
        if self.closing or self.service_busy or not self.service_queue:
            return

        self.service_busy = True

        (
            request_file,
            response_file,
            lines,
            callback,
            timeout,
        ) = self.service_queue.pop(0)

        request_id = uuid.uuid4().hex
        self.service_request_id = request_id

        # Request IDs are harmless to services that ignore unknown keys.
        request_lines = [f"request_id={request_id}", *lines]

        self._clear_service_files(request_file, response_file)

        try:
            self._atomic_write(
                request_file,
                "\n".join(request_lines) + "\n",
            )
        except OSError as exc:
            self.service_busy = False
            self.service_request_id = None
            callback({
                "status": "failure",
                "message": f"Could not write service request: {exc}",
            })
            self._process_service_queue()
            return

        started = time.monotonic()

        def poll() -> None:
            if self.closing:
                self.service_busy = False
                self.service_request_id = None
                return

            if response_file.exists():
                response = parse_key_value_response(response_file)

                response_id = response.get("request_id")
                if response_id and response_id != request_id:
                    self.after(SERVICE_POLL_MS, poll)
                    return

                try:
                    response_file.unlink()
                except OSError:
                    pass

                self.service_busy = False
                self.service_request_id = None

                callback(response)
                self._process_service_queue()
                return

            elapsed_ms = (time.monotonic() - started) * 1000
            if elapsed_ms >= timeout:
                self.service_busy = False
                self.service_request_id = None

                callback({
                    "status": "failure",
                    "message": "Microservice response timed out.",
                })

                self._process_service_queue()
                return

            self.after(SERVICE_POLL_MS, poll)

        self.after(SERVICE_POLL_MS, poll)

    @staticmethod
    def handle_save_response(response: dict[str, str]) -> bool:
        return response.get("status", "").lower() == "success"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_current_state(
        self,
        callback: Optional[Callable[[bool], None]] = None,
    ) -> None:
        """Save the current user's complete game list through save.py."""
        if not self.username:
            if callback:
                callback(False)
            return

        payload = json.dumps(
            self.games,
            separators=(",", ":"),
        )

        def finished(response: dict[str, str]) -> None:
            success = self.handle_save_response(response)

            if not success:
                print(
                    "Save service:",
                    response.get("message", "Save failed."),
                )

            if callback:
                callback(success)

        self._send_service_request(
            SAVE_REQUEST,
            SAVE_RESPONSE,
            [
                f"username={self.username}",
                f"file_name={GAME_DATA_FILE}",
                f"save_data={payload}",
            ],
            finished,
        )

    @staticmethod
    def _extract_saved_games(
        response: dict[str, str],
    ) -> Optional[list[dict[str, Any]]]:
        """Extract the game list returned by read.py."""
        raw_data = response.get("data")

        if not raw_data:
            return None

        try:
            parsed = json.loads(raw_data)
        except json.JSONDecodeError:
            return None

        # The expected JSON format is a list of game dictionaries.
        if isinstance(parsed, list):
            return [
                normalize_game(game)
                for game in parsed
                if isinstance(game, dict)
            ]

        # Also accept {"games": [...]} so older/alternate files
        # can still be read without breaking the client.
        if isinstance(parsed, dict):
            games = parsed.get("games")

            if isinstance(games, list):
                return [
                    normalize_game(game)
                    for game in games
                    if isinstance(game, dict)
                ]

        return None

    def load_saved_state(self) -> None:
        """Load the logged-in user's game list through read.py."""
        if not self.username:
            self.games = []
            self.show_main("Active")
            return

        self.data_loading = True

        self._send_service_request(
            READ_REQUEST,
            READ_RESPONSE,
            [
                "command=READ",
                f"username={self.username}",
                f"file_name={GAME_DATA_FILE}",
            ],
            self.handle_saved_state_response,
        )

    def handle_saved_state_response(
        self,
        response: dict[str, str],
    ) -> None:
        """Handle the JSON returned by read.py."""
        self.data_loading = False

        status = response.get("status", "").lower()

        if status == "success":
            games = self._extract_saved_games(response)

            if games is not None:
                self.games = games
            else:
                # A successful response with unusable JSON should not
                # silently create or preserve stale game data.
                self.games = []
                messagebox.showwarning(
                    "Saved Data",
                    "The saved game JSON could not be understood. "
                    "Starting with an empty collection.",
                )

        elif status == "failure":
            # A missing JSON file is normal for a first-time user.
            # Do not treat it as an application error; save.py will create
            # the file the first time game data is saved.
            message = response.get("message", "")

            if message.lower() == "file not found":
                self.games = []
            else:
                self.games = []
                if message:
                    print(f"Read service: {message}")

        else:
            self.games = []

        self.show_main("Active")
        self.request_streak()

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def show_login(self) -> None:
        self.clear()
        self.current_page = "login"

        page = tk.Frame(self.root_container, bg=PANEL)
        page.pack(fill="both", expand=True)
        self._draw_background(page)

        header = tk.Frame(page, bg="#151313", height=180)
        header.place(relx=0, rely=0, relwidth=1, height=180)

        self.title_label(header).place(x=85, y=43)

        body = tk.Frame(page, bg=PANEL)
        body.place(x=2, y=180, relwidth=0.996, relheight=0.74)

        tk.Label(
            body,
            text=(
                "Use this app to\nkeep track of\nyour game\ncollection and\n"
                "your progress\ntowards beating\nthem."
            ),
            bg=PANEL,
            fg=BLACK,
            justify="left",
            font=("Arial", 16),
        ).place(x=225, y=120)

        tk.Label(
            body,
            text="Log In",
            bg=PANEL,
            fg=BLACK,
            font=("Arial", 36, "bold"),
        ).place(x=665, y=50)

        self.username_entry = tk.Entry(
            body,
            font=("Arial", 15),
            width=18,
        )
        self.username_entry.insert(0, "")
        self.username_entry.place(x=654, y=123)

        self.password_entry = tk.Entry(
            body,
            font=("Arial", 15),
            width=18,
            show="*",
        )
        self.password_entry.insert(0, "")
        self.password_entry.place(x=654, y=196)

        self.login_status = tk.Label(
            body,
            text="",
            bg=PANEL,
            fg=RED,
            font=("Arial", 11),
        )
        self.login_status.place(x=654, y=235)

        self.make_button(
            body,
            "Go",
            self.login,
            width=5,
        ).place(x=767, y=254)

        self.username_entry.focus_set()
        self.username_entry.bind("<Return>", lambda _event: self.login())
        self.password_entry.bind("<Return>", lambda _event: self.login())

    def login(self) -> None:
        if self.login_pending:
            return

        if self.username_entry is None or self.password_entry is None:
            return

        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            if self.login_status:
                self.login_status.config(
                    text="Enter username and password.",
                    fg=RED,
                )
            return

        self.login_pending = True

        if self.login_status:
            self.login_status.config(
                text="Logging in...",
                fg=BLACK,
            )

        self._send_service_request(
            LOGIN_REQUEST,
            LOGIN_RESPONSE,
            [
                f"username={username}",
                f"password={password}",
            ],
            self.handle_login_response,
        )

    def handle_login_response(
        self,
        response: dict[str, str],
    ) -> None:
        self.login_pending = False

        if response.get("status", "").lower() == "success":
            self.username = response.get(
                "username",
                self.username_entry.get().strip()
                if self.username_entry
                else "",
            )

            self.load_saved_state()
            return

        if self.login_status:
            self.login_status.config(
                text=response.get("message", "Login failed."),
                fg=RED,
            )

    # ------------------------------------------------------------------
    # Streak / reminder
    # ------------------------------------------------------------------

    def request_streak(self) -> None:
        if not self.username:
            return

        self._send_service_request(
            STREAK_REQUEST,
            STREAK_RESPONSE,
            [
                "command=GET_STREAK",
                f"user={self.username}",
            ],
            self.handle_streak_response,
        )

    def handle_streak_response(
        self,
        response: dict[str, str],
    ) -> None:
        if (
            self.streak_label is None
            or not self.streak_label.winfo_exists()
        ):
            return

        streak = response.get("current_streak", "0")
        self.streak_label.config(text=f"Streak: {streak} days")


    def poll_reminder_response(self) -> None:
        if self.closing:
            return

        if REMINDER_RESPONSE.exists():
            try:
                response = parse_key_value_response(REMINDER_RESPONSE)

                if response.get("event", "").upper() == "ALERT":
                    message = response.get(
                        "message",
                        "Time to start today's session!",
                    )
                    messagebox.showinfo(
                        "Session Reminder",
                        message,
                    )
                else:
                    raw = REMINDER_RESPONSE.read_text(
                        encoding="utf-8"
                    ).strip()

                    if raw.startswith("ALERT"):
                        messagebox.showinfo(
                            "Session Reminder",
                            "Time to start today's session!",
                        )

                REMINDER_RESPONSE.unlink()
            except OSError:
                pass

        self.after(REMINDER_POLL_MS, self.poll_reminder_response)

    def set_reminder(self, time_value: str) -> None:
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time_value):
            messagebox.showwarning(
                "Session Reminder",
                "Enter a valid time in HH:MM format.",
            )
            return

        try:
            self._atomic_write(
                REMINDER_REQUEST,
                f"SET_TIME\n{time_value}\n",
            )
        except OSError as exc:
            messagebox.showerror(
                "Session Reminder",
                f"Could not set reminder: {exc}",
            )

    def clear_reminder(self) -> None:
        try:
            self._atomic_write(
                REMINDER_REQUEST,
                "CLEAR\n",
            )
        except OSError as exc:
            messagebox.showerror(
                "Session Reminder",
                f"Could not clear reminder: {exc}",
            )

    # ------------------------------------------------------------------
    # Main shell
    # ------------------------------------------------------------------

    def show_main(self, tab: str = "Active") -> None:
        self.clear()
        self.current_page = tab.lower()

        page = tk.Frame(self.root_container, bg=PANEL)
        page.pack(fill="both", expand=True)
        self._draw_background(page)

        header = tk.Frame(page, bg="#151313", height=180)
        header.place(x=0, y=0, relwidth=1, height=180)

        self.title_label(header).place(x=85, y=42)

        self.search_entry = tk.Entry(
            header,
            textvariable=self.search_var,
            font=("Arial", 14),
            width=18,
        )
        self.search_entry.place(x=734, y=21, height=35)
        self.search_entry.bind("<Return>", lambda _event: self.search_game())

        self.make_button(
            header,
            "⚙",
            self.show_settings,
            bg=WHITE,
            font=("Arial", 24),
            width=2,
        ).place(x=946, y=20, height=50)

        tabs = [
            ("Active", 40),
            ("Paused", 260),
            ("History", 480),
            ("Collection", 700),
        ]

        for label, x in tabs:
            selected = tab.lower() == label.lower()

            button = self.make_button(
                page,
                label,
                lambda name=label: self.show_main(name),
                bg=WHITE if selected else TAB_BLUE,
                font=("Arial", 16),
                width=12,
            )

            button.place(x=x, y=138, width=210, height=42)

        self.make_button(
            page,
            "+",
            self.show_add_game,
            bg=TAB_BLUE,
            font=("Arial", 25),
            width=2,
        ).place(x=918, y=132, height=48)

        self.streak_label = tk.Label(
            page,
            text=f"Streak: {self.request_streak() or '--'} days",
            bg=PANEL,
            fg=BLACK,
            font=("Arial", 12, "bold"),
        )
        self.streak_label.place(x=760, y=95)

        content = tk.Frame(page, bg=PANEL)
        content.place(
            x=2,
            y=180,
            relwidth=0.996,
            relheight=0.73,
        )

        if tab == "Active":
            self.build_active(content)
        elif tab == "Paused":
            self.build_paused(content)
        elif tab == "History":
            self.build_history(content)
        else:
            self.build_collection(content)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_game(self) -> None:
        """Search the games already loaded from the user's JSON file."""
        query = self.search_var.get().strip().lower()

        if not query:
            return

        matches = [
            game
            for game in self.games
            if query in game["title"].lower()
        ]

        if len(matches) == 1:
            self.show_game(matches[0])
        elif matches:
            self.show_search_results(matches)
        else:
            messagebox.showinfo(
                "Search",
                f"No game found for '{self.search_var.get().strip()}'.",
            )

    def show_search_results(
        self,
        matches: list[dict[str, Any]],
    ) -> None:
        win = self.popup_base(
            "Search Results",
            520,
            430,
        )

        tk.Label(
            win,
            text="Select a game",
            bg=WHITE,
            font=("Arial", 22, "bold"),
        ).pack(pady=15)

        for game in matches:
            self.make_button(
                win,
                game["title"],
                lambda g=game, w=win: (
                    w.destroy(),
                    self.show_game(g),
                ),
                bg=WHITE,
                font=("Arial", 14),
            ).pack(
                fill="x",
                padx=40,
                pady=6,
                ipady=7,
            )

    # ------------------------------------------------------------------
    # Game lists
    # ------------------------------------------------------------------

    def filtered_games(
        self,
        status: str,
    ) -> list[dict[str, Any]]:
        return [
            game for game in self.games
            if game["status"] == status
        ]

    def build_active(self, parent: tk.Frame) -> None:
        games = self.filtered_games("Active")

        if games:
            self.build_featured_active(
                parent,
                games[0],
                games[1:3],
            )

        y = 278

        for game in games[3:]:
            self.build_simple_row(parent, game, y)
            y += 70

    def build_featured_active(
        self,
        parent: tk.Frame,
        main: dict[str, Any],
        side: list[dict[str, Any]],
    ) -> None:
        big = self.card(parent)
        big.place(x=37, y=30, width=503, height=240)

        self.add_cover(
            big,
            main,
            25,
            18,
            110,
            160,
        )

        tk.Label(
            big,
            text=main["title"],
            bg=WHITE,
            fg="black",
            font=("Arial", 10, "bold"),
            wraplength=115,
            justify="center",
        ).place(
            x=26,
            y=183,
            width=108,
            height=40,
        )

        timer_button = self.make_button(
            big,
            self.timer_button_text(main),
            lambda g=main: self.toggle_timer(g),
            bg=self.timer_button_color(main),
            font=("Arial", 18),
        )
        timer_button.place(
            x=140,
            y=18,
            width=207,
            height=98,
        )
        self.register_timer_control(main, timer_button)

        self.make_button(
            big,
            "Beat It!",
            lambda g=main: self.mark_beaten(g),
            bg=YELLOW,
            font=("Arial", 16),
        ).place(
            x=357,
            y=18,
            width=140,
            height=98,
        )

        self.make_button(
            big,
            "Add Time",
            lambda g=main: self.add_time(g),
            bg=BLUE,
            font=("Arial", 18),
        ).place(
            x=140,
            y=126,
            width=207,
            height=98,
        )

        self.make_button(
            big,
            "Pause\nPlaythrough",
            lambda g=main: self.pause_game(g),
            bg=RED,
            font=("Arial", 15),
        ).place(
            x=357,
            y=126,
            width=140,
            height=98,
        )


        y = 30

        for game in side:
            card = self.card(parent)
            card.place(
                x=560,
                y=y,
                width=436,
                height=108,
            )

            self.add_cover(
                card,
                game,
                8,
                10,
                65,
                88,
            )

            self.make_button(
                card,
                game["title"],
                lambda g=game: self.show_game(g),
                bg=WHITE,
                font=("Arial", 12),
            ).place(
                x=85,
                y=8,
                width=160,
                height=28,
            )

            timer_label = tk.Label(
                card,
                text=self.timer_display_text(game),
                bg=WHITE,
                font=("Arial", 12),
                relief="solid",
                bd=1,
            )
            timer_label.place(
                x=85,
                y=43,
                width=160,
                height=27,
            )

            self.mini_action_buttons(
                card,
                game,
                270,
                16,
                timer_label,
            )

            y += 120

    def timer_button_color(self, game: dict[str, Any]) -> str:
        return RED if self.timer_running and self.timer_game is game else GREEN

    def timer_display_text(self, game: dict[str, Any]) -> str:
        return self.live_time_text(game)

    def timer_button_text(self, game: dict[str, Any]) -> str:
        state = "STOP" if self.timer_running and self.timer_game is game else "START"
        return f"{state}\n{self.timer_display_text(game)}"

    def live_seconds(self, game: dict[str, Any]) -> float:
        base_seconds = float(game.get("playtime", 0)) * 60

        if self.timer_running and self.timer_game is game:
            return base_seconds + (
                time.monotonic() - self.timer_started_at
            )

        return base_seconds

    def live_minutes(self, game: dict[str, Any]) -> int:
        return int(self.live_seconds(game) / 60)

    def live_time_text(self, game: dict[str, Any]) -> str:
        total_seconds = max(0, int(self.live_seconds(game)))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def register_timer_control(
        self,
        game: dict[str, Any],
        button: tk.Button,
        label: Optional[tk.Label] = None,
    ) -> None:
        self.timer_controls.append((game, button, label))
        self._update_timer_control(game, button, label)

    def _update_timer_control(
        self,
        game: dict[str, Any],
        button: tk.Button,
        label: Optional[tk.Label],
    ) -> None:
        if not button.winfo_exists():
            return

        active = self.timer_running and self.timer_game is game
        color = RED if active else GREEN
        
        button_text = self.timer_button_text(game) if label is None else " "
        button.config(
            text=button_text,
            bg=color,
            activebackground=color,
        )

        if label is not None and label.winfo_exists():
            label.config(text=self.timer_display_text(game))

    def mini_action_buttons(
        self,
        parent: tk.Frame,
        game: dict[str, Any],
        x: int,
        y: int,
        timer_label: tk.Label,
    ) -> None:
        timer_button = self.make_button(
            parent,
            " ",
            lambda g=game: self.toggle_timer(g),
            bg=self.timer_button_color(game),
            font=("Arial", 13),
        )
        timer_button.place(
            x=x,
            y=y,
            width=35,
            height=35,
        )
        self.register_timer_control(game, timer_button, timer_label)

        self.make_button(
            parent,
            " ",
            lambda g=game: self.mark_beaten(g),
            bg=YELLOW,
            font=("Arial", 13),
        ).place(
            x=x + 39,
            y=y,
            width=35,
            height=35,
        )

        self.make_button(
            parent,
            " ",
            lambda g=game: self.add_time(g),
            bg=BLUE,
            font=("Arial", 15),
        ).place(
            x=x + 78,
            y=y,
            width=35,
            height=35,
        )

        self.make_button(
            parent,
            " ",
            lambda g=game: self.pause_game(g),
            bg=RED,
            font=("Arial", 13),
        ).place(
            x=x + 117,
            y=y,
            width=35,
            height=35,
        )

    def build_simple_row(
        self,
        parent: tk.Frame,
        game: dict[str, Any],
        y: int,
    ) -> None:
        card = self.card(parent)
        card.place(
            x=37,
            y=y,
            width=959,
            height=45,
        )

        # Game title
        self.make_button(
            card,
            game["title"],
            lambda g=game: self.show_game(g),
            bg=WHITE,
            font=("Arial", 10),
        ).place(
            x=18,
            y=8,
            width=260,
            height=29,
        )

        # Live/current playtime
        timer_label = tk.Label(
            card,
            text=self.timer_display_text(game),
            bg=WHITE,
            font=("Arial", 10),
            relief="solid",
            bd=1,
        )
        timer_label.place(
            x=288,
            y=8,
            width=175,
            height=29,
        )

        # Start / Stop
        timer_button = self.make_button(
            card,
            None,
            lambda g=game: self.toggle_timer(g),
            bg=self.timer_button_color(game),
            font=("Arial", 11),
        )
        timer_button.place(
            x=595,
            y=8,
            width=80,
            height=29,
        )
        self.register_timer_control(game, timer_button, timer_label)

        # Beat
        self.make_button(
            card,
            " ",
            lambda g=game: self.mark_beaten(g),
            bg=YELLOW,
            font=("Arial", 11),
        ).place(
            x=685,
            y=8,
            width=80,
            height=29,
        )

        # Add Time
        self.make_button(
            card,
            " ",
            lambda g=game: self.add_time(g),
            bg=BLUE,
            font=("Arial", 18),
        ).place(
            x=775,
            y=8,
            width=80,
            height=29,
        )

        # Pause
        self.make_button(
            card,
            " ",
            lambda g=game: self.pause_game(g),
            bg=RED,
            font=("Arial", 11),
        ).place(
            x=865,
            y=8,
            width=80,
            height=29,
        )


    @staticmethod
    def parse_estimated_minutes(estimated: str) -> int:
        if not estimated:
            return 0

        match = re.fullmatch(
            r"\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*",
            estimated.lower(),
        )

        if not match:
            return 0

        hours = safe_int(match.group(1), 0)
        minutes = safe_int(match.group(2), 0)

        return hours * 60 + minutes

    def time_left(self, game: dict[str, Any]) -> str:
        estimated = self.parse_estimated_minutes(
            game.get("estimated", "")
        )

        return fmt_time(
            max(
                0,
                estimated - self.live_minutes(game),
            )
        )

    def build_paused(self, parent: tk.Frame) -> None:
        games = self.filtered_games("Paused")

        headings = [
            "Title",
            "Playtime",
            "Time Left",
            "Days Since\nPause",
        ]

        for i, text in enumerate(headings):
            tk.Label(
                parent,
                text=text,
                bg=PANEL,
                font=("Arial", 13, "bold"),
            ).place(
                x=40 + i * 230,
                y=18,
            )

        y = 65

        for game in games:
            card = self.card(parent)
            card.place(
                x=37,
                y=y,
                width=959,
                height=72,
            )

            tk.Label(
                card,
                text=game["title"],
                bg=WHITE,
                font=("Arial", 13),
                relief="solid",
                bd=1,
            ).place(
                x=18,
                y=12,
                width=205,
                height=45,
            )

            tk.Label(
                card,
                text=fmt_time(game["playtime"]),
                bg=WHITE,
                font=("Arial", 13),
                relief="solid",
                bd=1,
            ).place(
                x=238,
                y=12,
                width=150,
                height=45,
            )

            tk.Label(
                card,
                text=self.time_left(game),
                bg=WHITE,
                font=("Arial", 13),
                relief="solid",
                bd=1,
            ).place(
                x=400,
                y=12,
                width=150,
                height=45,
            )

            tk.Label(
                card,
                text=f'{game.get("days_paused", 0)} Days Ago',
                bg=WHITE,
                font=("Arial", 13),
                relief="solid",
                bd=1,
            ).place(
                x=565,
                y=12,
                width=170,
                height=45,
            )

            self.make_button(
                card,
                "Resume",
                lambda g=game: self.resume_game(g),
                bg=GREEN,
                font=("Arial", 12),
            ).place(
                x=760,
                y=12,
                width=90,
                height=45,
            )

            self.make_button(
                card,
                "Open",
                lambda g=game: self.show_game(g),
                bg=YELLOW,
                font=("Arial", 12),
            ).place(
                x=860,
                y=12,
                width=80,
                height=45,
            )

            y += 82

    def build_history(self, parent: tk.Frame) -> None:
        games = self.filtered_games("History")

        for i, game in enumerate(games):
            x = 37 + (i % 4) * 240
            y = 30 + (i // 4) * 180

            card = self.card(parent)
            card.place(
                x=x,
                y=y,
                width=220,
                height=155,
            )

            self.add_cover(
                card,
                game,
                10,
                10,
                62,
                85,
            )

            tk.Label(
                card,
                text=self.format_title(game["title"], 19),
                bg=WHITE,
                font=("Arial", 12),
                relief="solid",
                bd=1,
            ).place(
                x=82,
                y=12,
                width=125,
                height=34,
            )

            tk.Label(
                card,
                text=fmt_time(game["playtime"]),
                bg=WHITE,
                font=("Arial", 12),
                relief="solid",
                bd=1,
            ).place(
                x=82,
                y=55,
                width=125,
                height=34,
            )

            tk.Label(
                card,
                text="Beat!",
                bg=GREEN,
                font=("Arial", 12),
                relief="solid",
                bd=1,
            ).place(
                x=82,
                y=100,
                width=125,
                height=34,
            )

    def build_collection(self, parent: tk.Frame) -> None:
        games = self.filtered_games("Collection")

        for i, game in enumerate(games):
            x = 37 + (i % 4) * 240
            y = 30 + (i // 4) * 180

            card = self.card(parent)
            card.place(
                x=x,
                y=y,
                width=220,
                height=155,
            )

            self.add_cover(
                card,
                game,
                10,
                10,
                62,
                85,
            )

            self.make_button(
                card,
                self.format_title(game["title"], 19),
                lambda g=game: self.show_game(g),
                bg=WHITE,
                font=("Arial", 11),
            ).place(
                x=82,
                y=12,
                width=125,
                height=34,
            )

            tk.Label(
                card,
                text="In Collection",
                bg=TAB_BLUE,
                font=("Arial", 11),
                relief="solid",
                bd=1,
            ).place(
                x=82,
                y=55,
                width=125,
                height=34,
            )

            self.make_button(
                card,
                "Start Playthrough",
                lambda g=game: self.start_collection_game(g),
                bg=GREEN,
                font=("Arial", 10),
            ).place(
                x=20,
                y=105,
                width=187,
                height=34,
            )

    # ------------------------------------------------------------------
    # Game detail
    # ------------------------------------------------------------------

    def show_game(self, game: dict[str, Any]) -> None:
        self.clear()
        self.current_page = "game"

        page = tk.Frame(self.root_container, bg=PANEL)
        page.pack(fill="both", expand=True)
        self._draw_background(page)

        header = tk.Frame(page, bg="#151313", height=180)
        header.place(
            x=0,
            y=0,
            relwidth=1,
            height=180,
        )

        self.title_label(header).place(x=85, y=42)

        self.make_button(
            header,
            "Search",
            self.focus_search,
            bg=WHITE,
            font=("Arial", 13),
        ).place(
            x=735,
            y=21,
            width=185,
            height=35,
        )

        self.make_button(
            header,
            "⚙",
            self.show_settings,
            bg=WHITE,
            font=("Arial", 24),
            width=2,
        ).place(
            x=946,
            y=20,
            height=50,
        )

        self.make_button(
            page,
            "← Back",
            lambda: self.show_main("Active"),
            bg=TAB_BLUE,
            font=("Arial", 13),
        ).place(
            x=40,
            y=135,
            width=120,
            height=40,
        )

        body = tk.Frame(page, bg=PANEL)
        body.place(
            x=2,
            y=180,
            relwidth=0.996,
            relheight=0.73,
        )

        self.add_cover(
            body,
            game,
            45,
            35,
            190,
            260,
        )

        tk.Label(
            body,
            text=game["title"],
            bg=PANEL,
            font=("Arial", 28, "bold"),
        ).place(
            x=270,
            y=38,
        )

        self.make_button(
            body,
            "Basic Analytics",
            lambda: None,
            bg=WHITE,
            font=("Arial", 14),
        ).place(
            x=270,
            y=100,
            width=190,
            height=40,
        )

        self.make_button(
            body,
            "History",
            lambda: self.show_game_history(game),
            bg=TAB_BLUE,
            font=("Arial", 14),
        ).place(
            x=465,
            y=100,
            width=120,
            height=40,
        )

        analytics = tk.Frame(
            body,
            bg=PANEL_DARK,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        analytics.place(
            x=270,
            y=155,
            width=675,
            height=245,
        )

        fields = [
            ("Rating", "—"),
            ("Time Played", None),
            ("Play Sessions", str(game["sessions"])),
            (
                "Started",
                game["started"] or "Not started",
            ),
            (
                "Beat?",
                "Y" if game["status"] == "History" else "N",
            ),
        ]

        for i, (label, value) in enumerate(fields):
            x = 20 + (i % 3) * 215
            y = 20 + (i // 3) * 85

            tk.Label(
                analytics,
                text=label,
                bg=PANEL_DARK,
                fg="white",
                font=("Arial", 12, "bold"),
            ).place(
                x=x,
                y=y,
            )

            if label == "Time Played":
                timer_value = (
                    self.live_time_text(game)
                    if self.timer_running and self.timer_game is game
                    else self.timer_display_text(game)
                )

                timer_label = tk.Label(
                    analytics,
                    text=timer_value,
                    bg=WHITE,
                    font=("Arial", 14),
                    relief="solid",
                    bd=1,
                )

                timer_label.place(
                    x=x,
                    y=y + 25,
                    width=185,
                    height=38,
                )

                self.active_timer_label = timer_label

        else:
            tk.Label(
                analytics,
                text=value,
                bg=WHITE,
                font=("Arial", 14),
                relief="solid",
                bd=1,
            ).place(
                x=x,
                y=y + 25,
                width=185,
                height=38,
            )

        if game.get("review"):
            tk.Label(
                body,
                text=game["review"],
                bg=PANEL,
                font=("Arial", 13),
                wraplength=600,
                justify="left",
            ).place(
                x=270,
                y=420,
            )

    @staticmethod
    def show_game_history(game: dict[str, Any]) -> None:
        messagebox.showinfo(
            "History",
            f"{game['title']}\n\n"
            f"Sessions: {game['sessions']}\n"
            f"Playtime: {fmt_time(game['playtime'])}\n"
            f"Started: {game['started'] or 'Not started'}",
        )

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def show_month(self) -> None:
        self.clear()

        page = tk.Frame(self.root_container, bg=PANEL)
        page.pack(fill="both", expand=True)
        self._draw_background(page)

        header = tk.Frame(page, bg="#151313", height=180)
        header.place(
            x=0,
            y=0,
            relwidth=1,
            height=180,
        )

        self.title_label(header).place(x=85, y=42)

        self.make_button(
            header,
            "Search",
            self.focus_search,
            bg=WHITE,
            font=("Arial", 13),
        ).place(
            x=735,
            y=21,
            width=185,
            height=35,
        )

        self.make_button(
            header,
            "⚙",
            self.show_settings,
            bg=WHITE,
            font=("Arial", 24),
            width=2,
        ).place(
            x=946,
            y=20,
            height=50,
        )

        body = tk.Frame(page, bg=PANEL)
        body.place(
            x=2,
            y=180,
            relwidth=0.996,
            relheight=0.73,
        )

        tk.Label(
            body,
            text=time.strftime("%B"),
            bg=PANEL,
            font=("Arial", 26, "bold"),
        ).place(
            x=45,
            y=25,
        )

        stats = self.calculate_current_stats()

        for i, (label, value) in enumerate(stats):
            x = 45 + (i % 3) * 300
            y = 75 + (i // 3) * 95

            card = self.card(body)
            card.place(
                x=x,
                y=y,
                width=270,
                height=80,
            )

            tk.Label(
                card,
                text=label,
                bg=PANEL_DARK,
                fg="white",
                font=("Arial", 12),
            ).place(
                x=10,
                y=10,
            )

            tk.Label(
                card,
                text=value,
                bg=WHITE,
                font=("Arial", 18),
                relief="solid",
                bd=1,
            ).place(
                x=10,
                y=36,
                width=240,
                height=34,
            )

        chart = self.card(body)
        chart.place(
            x=45,
            y=285,
            width=510,
            height=210,
        )

        tk.Label(
            chart,
            text="Current Month Activity By Game",
            bg=PANEL_DARK,
            fg="white",
            font=("Arial", 14, "bold"),
        ).pack(pady=10)

        self.draw_pie_chart(chart)

        chart2 = self.card(body)
        chart2.place(
            x=580,
            y=285,
            width=416,
            height=210,
        )

        tk.Label(
            chart2,
            text="Current Collection Playtime",
            bg=PANEL_DARK,
            fg="white",
            font=("Arial", 14, "bold"),
        ).pack(pady=10)

        self.draw_bar_chart(chart2)

    def calculate_current_stats(self) -> list[tuple[str, str]]:
        active_or_finished = [
            game for game in self.games
            if game["status"] != "Collection"
        ]

        games_played = len([
            game for game in active_or_finished
            if game["sessions"] > 0
        ])

        games_beaten = len(
            self.filtered_games("History")
        )

        total_minutes = sum(
            float(game["playtime"])
            for game in self.games
        )

        longest_streak = "--"

        return [
            ("Games Played", str(games_played)),
            ("Games Beaten", str(games_beaten)),
            ("Hours Played", fmt_time(total_minutes)),
            ("Total Sessions", str(sum(
                game["sessions"] for game in self.games
            ))),
            ("Longest Streak", longest_streak),
        ]

    @staticmethod
    def draw_pie_chart(parent: tk.Frame) -> None:
        canvas = tk.Canvas(
            parent,
            bg=PANEL_DARK,
            highlightthickness=0,
        )

        canvas.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=5,
        )

        values = [35, 25, 18, 12, 10]
        colors = [
            GREEN,
            YELLOW,
            BLUE,
            RED,
            "#8f8f8f",
        ]

        start = 0

        for value, color in zip(values, colors):
            extent = 360 * value / 100

            canvas.create_arc(
                85,
                15,
                235,
                165,
                start=start,
                extent=extent,
                fill=color,
                outline=BLACK,
            )

            start += extent

    @staticmethod
    def draw_bar_chart(parent: tk.Frame) -> None:
        canvas = tk.Canvas(
            parent,
            bg=PANEL_DARK,
            highlightthickness=0,
        )

        canvas.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=5,
        )

        values = [56, 20, 47]
        labels = ["June", "July", "August"]
        colors = [GREEN, YELLOW, BLUE]

        max_value = max(values)

        for i, (value, label) in enumerate(
            zip(values, labels)
        ):
            x = 40 + i * 115
            h = 120 * value / max_value

            canvas.create_rectangle(
                x,
                155 - h,
                x + 70,
                155,
                fill=colors[i],
                outline=BLACK,
            )

            canvas.create_text(
                x + 35,
                172,
                text=label,
                fill="white",
                font=("Arial", 10),
            )

            canvas.create_text(
                x + 35,
                145 - h,
                text=f"{value}h",
                fill="white",
                font=("Arial", 10),
            )

    # ------------------------------------------------------------------
    # Settings / add-game
    # ------------------------------------------------------------------

    def popup_base(
        self,
        title: str,
        width: int = 560,
        height: int = 430,
    ) -> tk.Toplevel:
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry(f"{width}x{height}")
        win.configure(bg=WHITE)
        win.transient(self)
        win.grab_set()
        return win

    def show_settings(self) -> None:
        win = self.popup_base(
            "Settings",
            560,
            430,
        )

        tk.Label(
            win,
            text="settings",
            bg=WHITE,
            font=("Arial", 25),
        ).pack(
            fill="x",
            pady=(15, 10),
        )

        self.make_button(
            win,
            "Change Theme",
            lambda: messagebox.showinfo(
                "Theme",
                "Theme options can be connected here.",
            ),
            bg=WHITE,
            font=("Arial", 15),
        ).pack(
            fill="x",
            padx=35,
            pady=10,
            ipady=8,
        )

        self.make_button(
            win,
            "Custom Theme",
            lambda: messagebox.showinfo(
                "Custom Theme",
                "Custom theme editor placeholder.",
            ),
            bg=WHITE,
            font=("Arial", 15),
        ).pack(
            fill="x",
            padx=35,
            pady=10,
            ipady=8,
        )

        self.make_button(
            win,
            "Customize Chart Details",
            lambda: messagebox.showinfo(
                "Charts",
                "Chart customization placeholder.",
            ),
            bg=WHITE,
            font=("Arial", 15),
        ).pack(
            fill="x",
            padx=35,
            pady=10,
            ipady=8,
        )

        self.make_button(
            win,
            "Month Statistics",
            lambda: (
                win.destroy(),
                self.show_month(),
            ),
            bg=TAB_BLUE,
            font=("Arial", 15),
        ).pack(
            fill="x",
            padx=35,
            pady=10,
            ipady=8,
        )

        self.make_button(
            win,
            "Session Reminder",
            self.show_reminder_settings,
            bg=TAB_BLUE,
            font=("Arial", 15),
        ).pack(
            fill="x",
            padx=35,
            pady=10,
            ipady=8,
        )

        self.make_button(
            win,
            "Log Out",
            lambda: self.logout(win),
            bg=RED,
            font=("Arial", 15),
        ).pack(
            fill="x",
            padx=35,
            pady=10,
            ipady=8,
        )

    def logout(self, settings_window: tk.Toplevel) -> None:
        if self.timer_running:
            self.stop_timer(save=False)

        self.save_current_state()

        settings_window.destroy()
        self.username = None
        self.search_var.set("")
        self.show_login()

    def show_reminder_settings(self) -> None:
        win = self.popup_base(
            "Session Reminder",
            360,
            250,
        )

        tk.Label(
            win,
            text="Reminder Time (HH:MM)",
            bg=WHITE,
            font=("Arial", 13),
        ).pack(pady=20)

        entry = tk.Entry(
            win,
            font=("Arial", 16),
            justify="center",
        )

        entry.insert(0, "18:00")
        entry.pack()

        self.make_button(
            win,
            "Set Reminder",
            lambda: self._set_reminder_and_close(
                entry,
                win,
            ),
            bg=GREEN,
        ).pack(
            pady=15,
            ipadx=20,
            ipady=6,
        )

        self.make_button(
            win,
            "Clear Today's Reminder",
            lambda: (
                self.clear_reminder(),
                win.destroy(),
            ),
            bg=RED,
        ).pack(
            ipadx=10,
            ipady=6,
        )

    def _set_reminder_and_close(
        self,
        entry: tk.Entry,
        win: tk.Toplevel,
    ) -> None:
        value = entry.get().strip()

        if not re.fullmatch(
            r"(?:[01]\d|2[0-3]):[0-5]\d",
            value,
        ):
            messagebox.showwarning(
                "Session Reminder",
                "Enter a valid time in HH:MM format.",
            )
            return

        self.set_reminder(value)
        win.destroy()

    def search_database_for_add(
        self,
        search_entry: tk.Entry,
        title_entry: tk.Entry,
        estimated_entry: tk.Entry,
    ) -> None:
        """Search the user's loaded game collection for an existing game."""
        query = search_entry.get().strip().lower()

        if not query:
            messagebox.showwarning(
                "Search Games",
                "Enter a game title.",
            )
            return

        matches = [
            game
            for game in self.games
            if query in game["title"].lower()
        ]

        if not matches:
            messagebox.showinfo(
                "Search Games",
                "No matching games are in your collection.",
            )
            return

        if len(matches) == 1:
            game = matches[0]
            title_entry.delete(0, tk.END)
            title_entry.insert(0, game["title"])

            estimated = game.get("estimated", "")
            if estimated:
                estimated_entry.delete(0, tk.END)
                estimated_entry.insert(0, estimated)

            messagebox.showinfo(
                "Search Games",
                f"Found: {game['title']}",
            )
            return

        # If multiple games match, use the first exact match when possible.
        exact = next(
            (game for game in matches if game["title"].lower() == query),
            None,
        )

        if exact is not None:
            title_entry.delete(0, tk.END)
            title_entry.insert(0, exact["title"])

            estimated = exact.get("estimated", "")
            if estimated:
                estimated_entry.delete(0, tk.END)
                estimated_entry.insert(0, estimated)

            messagebox.showinfo(
                "Search Games",
                f"Found: {exact['title']}",
            )
            return

        self.show_add_search_results(
            matches,
            title_entry,
            estimated_entry,
        )

    def show_add_search_results(
        self,
        matches: list[dict[str, Any]],
        title_entry: tk.Entry,
        estimated_entry: tk.Entry,
    ) -> None:
        """Let the user choose one of several matching games."""
        win = self.popup_base(
            "Search Games",
            520,
            430,
        )

        tk.Label(
            win,
            text="Select a game",
            bg=WHITE,
            font=("Arial", 22, "bold"),
        ).pack(pady=15)

        def select(game: dict[str, Any]) -> None:
            title_entry.delete(0, tk.END)
            title_entry.insert(0, game["title"])

            estimated = game.get("estimated", "")
            if estimated:
                estimated_entry.delete(0, tk.END)
                estimated_entry.insert(0, estimated)

            win.destroy()

        for game in matches:
            self.make_button(
                win,
                game["title"],
                lambda g=game: select(g),
                bg=WHITE,
                font=("Arial", 14),
            ).pack(
                fill="x",
                padx=40,
                pady=6,
                ipady=7,
            )

    def show_add_game(self) -> None:
        win = self.popup_base(
            "Add to Collection",
            600,
            500,
        )

        tk.Label(
            win,
            text="add to collection",
            bg=WHITE,
            font=("Arial", 25),
        ).pack(
            fill="x",
            pady=(15, 10),
        )

        tk.Label(
            win,
            text="Search Games",
            bg=WHITE,
            font=("Arial", 14),
        ).pack(pady=(10, 2))

        search = tk.Entry(
            win,
            font=("Arial", 14),
        )

        search.pack(
            fill="x",
            padx=45,
            ipady=7,
        )

        tk.Label(
            win,
            text="Game Title",
            bg=WHITE,
            font=("Arial", 14),
        ).pack(pady=(15, 2))

        title = tk.Entry(
            win,
            font=("Arial", 14),
        )

        title.pack(
            fill="x",
            padx=45,
            ipady=7,
        )

        tk.Label(
            win,
            text="Estimated Playtime",
            bg=WHITE,
            font=("Arial", 14),
        ).pack(pady=(15, 2))

        estimated = tk.Entry(
            win,
            font=("Arial", 14),
        )

        estimated.pack(
            fill="x",
            padx=45,
            ipady=7,
        )

        row = tk.Frame(win, bg=WHITE)
        row.pack(
            fill="x",
            padx=45,
            pady=20,
        )

        self.make_button(
            row,
            "Search Games",
            lambda: self.search_database_for_add(
                search,
                title,
                estimated,
            ),
            bg=WHITE,
            font=("Arial", 13),
        ).pack(
            side="left",
            expand=True,
            fill="x",
            padx=(0, 5),
            ipady=8,
        )

        def add() -> None:
            name = (
                title.get().strip()
                or search.get().strip()
            )

            if not name:
                messagebox.showwarning(
                    "Add Game",
                    "Enter a game title.",
                )
                return

            if any(
                game["title"].lower() == name.lower()
                for game in self.games
            ):
                messagebox.showwarning(
                    "Add Game",
                    "That game is already in your collection.",
                )
                return

            self.games.append(
                normalize_game({
                    "title": name,
                    "playtime": 0,
                    "status": "Collection",
                    "cover": None,
                    "estimated": estimated.get().strip()
                    or "Unknown",
                    "sessions": 0,
                    "started": "",
                    "review": "",
                })
            )

            win.destroy()
            self.save_current_state()
            self.show_main("Collection")

        self.make_button(
            row,
            "Add Game",
            add,
            bg=GREEN,
            font=("Arial", 13),
        ).pack(
            side="left",
            expand=True,
            fill="x",
            padx=(5, 0),
            ipady=8,
        )

    # ------------------------------------------------------------------
    # Timer / game state
    # ------------------------------------------------------------------

    def toggle_timer(self, game: dict[str, Any]) -> None:
        if self.timer_running and self.timer_game is game:
            self.stop_timer(save=True)
        else:
            self.start_timer(game)

    def start_timer(self, game: dict[str, Any]) -> None:
        if self.timer_running:
            self.stop_timer(save=False)

        self.timer_game = game
        self.timer_running = True
        self.timer_started_at = time.monotonic()

        if game["status"] == "Collection":
            game["status"] = "Active"
            game["started"] = (
                game["started"]
                or time.strftime("%m/%d/%Y")
            )

        game["sessions"] += 1

        if self.username:
            self._send_service_request(
                STREAK_REQUEST,
                STREAK_RESPONSE,
                [
                    "command=START_SESSION",
                    f"user={self.username}",
                ],
                self.handle_streak_response,
            )

        self.save_current_state()
        self._timer_tick()

    def stop_timer(self, save: bool = True) -> None:
        if self.timer_running and self.timer_game is not None:
            elapsed_seconds = (
                time.monotonic()
                - self.timer_started_at
            )

            if elapsed_seconds > 0:
                self.timer_game["playtime"] += (
                    elapsed_seconds / 60
                )

        self.timer_running = False
        self.timer_game = None
        self.timer_started_at = 0.0

        if self.timer_job:
            try:
                self.after_cancel(self.timer_job)
            except tk.TclError:
                pass

            self.timer_job = None

        # Immediately return every visible timer control to its inactive state.
        self._refresh_timer_controls()

        if save:
            self.save_current_state()

    def _refresh_timer_controls(self) -> None:
        for game, button, label in list(self.timer_controls):
            try:
                self._update_timer_control(game, button, label)
            except tk.TclError:
                pass

    def _timer_tick(self) -> None:
        if not self.timer_running or self.timer_game is None:
            return

        # Use the same monotonic clock used when the timer started.
        self._refresh_timer_controls()

        # Refresh once per second.
        self.timer_job = self.after(TIMER_UPDATE_MS, self._timer_tick)

    def add_time(self, game: dict[str, Any]) -> None:
        win = self.popup_base(
            "Add Time",
            320,
            210,
        )

        tk.Label(
            win,
            text="Minutes to add",
            bg=WHITE,
            font=("Arial", 13),
        ).pack(pady=15)

        entry = tk.Entry(
            win,
            font=("Arial", 16),
            justify="center",
        )

        entry.insert(0, "30")
        entry.pack()

        def add() -> None:
            try:
                minutes = int(entry.get())

                if minutes < 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning(
                    "Add Time",
                    "Enter a non-negative integer.",
                )
                return

            game["playtime"] += minutes
            win.destroy()

            self.save_current_state()
            self.show_main("Active")

        self.make_button(
            win,
            "Add",
            add,
            bg=GREEN,
            font=("Arial", 13),
        ).pack(
            pady=15,
            ipadx=25,
            ipady=5,
        )

    def pause_game(self, game: dict[str, Any]) -> None:
        if self.timer_game is game:
            self.stop_timer(save=False)

        game["status"] = "Paused"
        game["days_paused"] = 0

        self.save_current_state()
        self.show_main("Paused")

    def resume_game(self, game: dict[str, Any]) -> None:
        game["status"] = "Active"

        self.save_current_state()
        self.show_main("Active")

    def mark_beaten(self, game: dict[str, Any]) -> None:
        if self.timer_game is game:
            self.stop_timer(save=False)

        game["status"] = "History"

        self.save_current_state()
        self.show_main("History")

    def start_collection_game(self, game: dict[str, Any]) -> None:
        game["status"] = "Active"
        game["started"] = (
            game["started"]
            or time.strftime("%m/%d/%Y")
        )

        self.save_current_state()
        self.show_main("Active")

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------

    def add_cover(
        self,
        parent: tk.Misc,
        game: dict[str, Any],
        x: int,
        y: int,
        w: int,
        h: int,
    ) -> None:
        cover_name = game.get("cover")
        path = (
            ASSET_DIR / cover_name
            if cover_name
            else None
        )

        if (
            Image is not None
            and ImageTk is not None
            and path is not None
            and path.exists()
        ):
            key = (
                str(path),
                w,
                h,
            )

            if key not in self.cover_cache:
                try:
                    with Image.open(path) as source:
                        image = source.convert("RGB")
                        image.thumbnail((w, h))
                        self.cover_cache[key] = (
                            ImageTk.PhotoImage(image)
                        )
                except OSError:
                    pass

            if key in self.cover_cache:
                label = tk.Label(
                    parent,
                    image=self.cover_cache[key],
                    bg=WHITE,
                    bd=1,
                    relief="solid",
                )
                label.place(
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                )
                return

        label = tk.Label(
            parent,
            text="ART",
            bg="#c9c9c9",
            fg=BLACK,
            font=("Arial", 16, "bold"),
            bd=1,
            relief="solid",
        )

        label.place(
            x=x,
            y=y,
            width=w,
            height=h,
        )

    @staticmethod
    def status_squares(
        parent: tk.Misc,
        x: int,
        y: int,
    ) -> None:
        for i, color in enumerate(
            [GREEN, YELLOW, BLUE, RED]
        ):
            tk.Label(
                parent,
                bg=color,
                bd=1,
                relief="solid",
            ).place(
                x=x + i * 70,
                y=y,
                width=50,
                height=40,
            )

    # ------------------------------------------------------------------
    # Navigation / shutdown
    # ------------------------------------------------------------------

    def focus_search(self) -> None:
        self.show_main("Active")

        if self.search_entry is not None:
            self.search_entry.focus_set()
            self.search_entry.select_range(
                0,
                tk.END,
            )

    def on_close(self) -> None:
        if self.closing:
            return

        if self.timer_running:
            self.stop_timer(save=False)

        if not self.username:
            self.closing = True
            self.destroy()
            return

        # Put the final save behind any already queued service requests.
        # The application closes only after the queue reaches this save.
        self.closing = False
        self.service_queue.append(
            (
                SAVE_REQUEST,
                SAVE_RESPONSE,
                [
                    f"username={self.username}",
                    f"file_name={GAME_DATA_FILE}",
                    f"save_data={json.dumps(self.games, separators=(',', ':'))}",
                ],
                self._finish_close_save,
                SERVICE_TIMEOUT_MS,
            )
        )
        self._process_service_queue()

    def _finish_close_save(self, _response: dict[str, str]) -> None:
        self.closing = True
        self.destroy()



if __name__ == "__main__":
    window = GameThroughApp()
    window.mainloop()
