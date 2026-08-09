
"""
GAMETHROUGH - desktop UI prototype
-----------------------------------
A Tkinter implementation based on the supplied Sprint design screens.

Run:
    python gamethrough_ui.py

The UI communicates with five independent text-file microservices: Read, Save,
Login, Remind, and Streak.
"""

from __future__ import annotations

import json
import time
import re
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "assets"

# Text-file microservice communication endpoints.
LOGIN_REQUEST = BASE_DIR / "login_request.txt"
LOGIN_RESPONSE = BASE_DIR / "login_response.txt"
READ_REQUEST = BASE_DIR / "read_request.txt"
READ_RESPONSE = BASE_DIR / "read_response.txt"
SAVE_REQUEST = BASE_DIR / "save_request.txt"
SAVE_RESPONSE = BASE_DIR / "save_response.txt"
REMINDER_REQUEST = BASE_DIR / "reminder_request.txt"
REMINDER_RESPONSE = BASE_DIR / "reminder_response.txt"
STREAK_REQUEST = BASE_DIR / "session_request.txt"
STREAK_RESPONSE = BASE_DIR / "session_response.txt"
USERS_FILE = BASE_DIR / "users.txt"

SERVICE_POLL_MS = 150
SERVICE_TIMEOUT_MS = 5000

# Colors sampled/approximated from the supplied design.
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


SAMPLE_GAMES = [
    {
        "title": "Super Mario Sunshine",
        "playtime": 4 * 60 + 35,
        "status": "Active",
        "cover": "super_mario_sunshine.jpg",
        "estimated": "15h",
        "sessions": 8,
        "started": "09/04/2025",
        "review": "Fantastic setting, wonderful gameplay, finicky polish.",
    },
    {
        "title": "Ristar",
        "playtime": 41,
        "status": "Active",
        "cover": "ristar.jpg",
        "estimated": "4h",
        "sessions": 2,
        "started": "08/14/2026",
        "review": "",
    },
    {
        "title": "Pokemon Snap",
        "playtime": 11 * 60 + 7,
        "status": "Active",
        "cover": "pokemon_snap.jpg",
        "estimated": "6h",
        "sessions": 5,
        "started": "08/02/2026",
        "review": "",
    },
    {
        "title": "Uncharted: Drake's Fortune",
        "playtime": 7 * 60 + 4,
        "status": "Active",
        "cover": None,
        "estimated": "8h",
        "sessions": 6,
        "started": "07/20/2026",
        "review": "",
    },
    {
        "title": "Blue Dragon",
        "playtime": 2 * 60 + 33,
        "status": "Active",
        "cover": None,
        "estimated": "35h",
        "sessions": 3,
        "started": "07/18/2026",
        "review": "",
    },
    {
        "title": "The Last of Us",
        "playtime": 6 * 60 + 20,
        "status": "Paused",
        "cover": None,
        "estimated": "15h",
        "sessions": 4,
        "started": "07/10/2026",
        "review": "",
        "days_paused": 13,
    },
    {
        "title": "Brute Force",
        "playtime": 43,
        "status": "Paused",
        "cover": None,
        "estimated": "7h",
        "sessions": 2,
        "started": "06/18/2026",
        "review": "",
        "days_paused": 50,
    },
    {
        "title": "RoboCop vs. The Terminator",
        "playtime": 2 * 60 + 4,
        "status": "Paused",
        "cover": None,
        "estimated": "4h",
        "sessions": 2,
        "started": "06/18/2026",
        "review": "",
        "days_paused": 50,
    },
    {
        "title": "PaRappa the Rapper 2",
        "playtime": 1 * 60 + 5,
        "status": "Paused",
        "cover": None,
        "estimated": "5h",
        "sessions": 1,
        "started": "06/18/2026",
        "review": "",
        "days_paused": 390,
    },
    {
        "title": "Final Fantasy IX",
        "playtime": 16 * 60 + 20,
        "status": "History",
        "cover": None,
        "estimated": "40h",
        "sessions": 20,
        "started": "08/01/2026",
        "review": "",
    },
    {
        "title": "Assassin's Creed",
        "playtime": 5 * 60 + 10,
        "status": "History",
        "cover": None,
        "estimated": "18h",
        "sessions": 9,
        "started": "08/03/2026",
        "review": "",
    },
    {
        "title": "I Have No Mouth and I Must Scream",
        "playtime": 10 * 60 + 20,
        "status": "History",
        "cover": None,
        "estimated": "6h",
        "sessions": 7,
        "started": "08/05/2026",
        "review": "",
    },
    {
        "title": "Fallout 3",
        "playtime": 15 * 60 + 29,
        "status": "History",
        "cover": None,
        "estimated": "30h",
        "sessions": 14,
        "started": "08/06/2026",
        "review": "",
    },
    {
        "title": "Call of Duty 2",
        "playtime": 8 * 60,
        "status": "Collection",
        "cover": None,
        "estimated": "8h",
        "sessions": 0,
        "started": "",
        "review": "",
    },
    {
        "title": "Jet Set Radio Future",
        "playtime": 0,
        "status": "Collection",
        "cover": None,
        "estimated": "12h",
        "sessions": 0,
        "started": "",
        "review": "",
    },
    {
        "title": "Okami HD",
        "playtime": 0,
        "status": "Collection",
        "cover": None,
        "estimated": "35h",
        "sessions": 0,
        "started": "",
        "review": "",
    },
]


def fmt_time(minutes: int) -> str:
    hours, mins = divmod(max(0, int(minutes)), 60)
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


class GameThroughApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GAMETHROUGH")
        self.geometry("1200x675")
        self.minsize(1000, 620)
        self.configure(bg=PANEL)

        self.games = [dict(g) for g in SAMPLE_GAMES]
        self.current_page = "login"
        self.username = None
        self.password = None
        self.streak_label = None
        self.login_pending = False
        self.service_waiters = {}
        self.search_var = tk.StringVar()
        self.timer_game: Optional[dict] = None
        self.timer_running = False
        self.timer_started_at = 0.0
        self.timer_job = None
        self.cover_cache = {}

        self.bg_image = None
        self.bg_photo = None
        self._load_background()

        self.root_container = tk.Frame(self, bg=PANEL)
        self.root_container.pack(fill="both", expand=True)
        self.ensure_sample_user()
        self.poll_reminder_response()

        self.show_login()

    # ---------- Shared visual helpers ----------

    def _load_background(self):
        if Image is None:
            return
        path = ASSET_DIR / "background.jpeg"
        if path.exists():
            self.bg_image = Image.open(path).convert("RGB")

    def _draw_background(self, parent, header_height=180):
        if Image is not None and self.bg_image is not None:
            width = max(parent.winfo_width(), 1200)
            height = max(parent.winfo_height(), 675)
            img = self.bg_image.resize((width, height))
            self.bg_photo = ImageTk.PhotoImage(img)
            label = tk.Label(parent, image=self.bg_photo, bd=0)
            label.place(x=0, y=0, relwidth=1, relheight=1)
        else:
            parent.configure(bg="#1d1a19")

    def clear(self):
        # Navigation should not terminate an active play session.
        for child in self.root_container.winfo_children():
            child.destroy()

    @staticmethod
    def title_label(parent, text="GAMETHROUGH"):
        return tk.Label(
            parent, text=text, font=("Arial", 32, "bold"),
            fg="white", bg="#151313"
        )

    @staticmethod
    def make_button(parent, text, command, bg=None, fg=None,
                    font=None, width=None):
        if bg is None:
            bg = WHITE
        if fg is None:
            fg = BLACK
        if font is None:
            font = ("Arial", 15)
        opts = dict(
            text=text, command=command, bg=bg, fg=fg,
            activebackground=bg, activeforeground=fg,
            relief="solid", bd=1, font=font, cursor="hand2"
        )
        if width is not None:
            opts["width"] = width
        return tk.Button(parent, **opts)

    @staticmethod
    def card(parent, **kwargs):
        return tk.Frame(parent, bg=PANEL_DARK, highlightbackground=BORDER,
                        highlightthickness=1, **kwargs)

    def format_title(self, title, max_len=25):
        return title if len(title) <= max_len else title[:max_len - 1] + "…"

    # ---------- Microservice communication ----------

    @staticmethod
    def ensure_sample_user():
        try:
            users = USERS_FILE.read_text(encoding="utf-8").splitlines() if USERS_FILE.exists() else []
            if not any(line.split(":", 1)[0] == "tester" for line in users if ":" in line):
                with USERS_FILE.open("a", encoding="utf-8") as file:
                    file.write("tester:app\n")
        except OSError:
            pass

    @staticmethod
    def _clear_service_files(request_file: Path, response_file: Path):
        for path in (request_file, response_file):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass

    def _send_service_request(self, request_file, response_file, lines, callback, timeout=SERVICE_TIMEOUT_MS):
        self._clear_service_files(request_file, response_file)
        try:
            request_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError as exc:
            callback({"status": "failure", "message": str(exc)})
            return

        started = time.monotonic()

        def poll():
            if response_file.exists():
                response = parse_key_value_response(response_file)
                try:
                    response_file.unlink()
                except OSError:
                    pass
                callback(response)
                return
            if (time.monotonic() - started) * 1000 >= timeout:
                callback({"status": "failure", "message": "Microservice response timed out."})
                return
            self.after(SERVICE_POLL_MS, poll)

        self.after(SERVICE_POLL_MS, poll)

    @staticmethod
    def handle_save_response(response):
        return response.get("status", "failure").lower() == "success"

    def save_current_state(self):
        if not self.username:
            return
        payload = json.dumps(self.games, separators=(",", ":"))
        self._send_service_request(
            SAVE_REQUEST, SAVE_RESPONSE,
            [
                f"username={self.username}",
                "file_name=gamethrough_data.json",
                f"save_data={payload}",
            ],
            self._finish_save
        )

    def _finish_save(self, response):
        if not self.handle_save_response(response):
            return

    def show_login(self):
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

        desc = tk.Label(
            body,
            text="Use this app to\nkeep track of\nyour game\ncollection and\nyour progress\ntowards beating\nthem.",
            bg=PANEL, fg=BLACK, justify="left",
            font=("Arial", 16)
        )
        desc.place(x=225, y=120)

        tk.Label(body, text="Log In", bg=PANEL, fg=BLACK,
                 font=("Arial", 36, "bold")).place(x=665, y=50)

        self.username = tk.Entry(body, font=("Arial", 15), width=18)
        self.username.insert(0, "tester")
        self.username.place(x=654, y=123)

        self.password = tk.Entry(body, font=("Arial", 15), width=18, show="*")
        self.password.insert(0, "app")
        self.password.place(x=654, y=196)

        self.login_status = tk.Label(body, text="", bg=PANEL, fg=RED, font=("Arial", 11))
        self.login_status.place(x=654, y=235)
        self.make_button(body, "Go", self.login, width=5).place(x=767, y=254)

    def login(self):
        if self.login_pending:
            return
        username = self.username.get().strip()
        password = self.password.get()
        if not username or not password:
            self.login_status.config(text="Enter username and password.")
            return
        self.login_pending = True
        self.login_status.config(text="Logging in...", fg=BLACK)
        self._send_service_request(
            LOGIN_REQUEST, LOGIN_RESPONSE,
            [f"username={username}", f"password={password}"],
            self.handle_login_response
        )

    def handle_login_response(self, response):
        self.login_pending = False
        if response.get("status", "").lower() == "success":
            self.username = response.get("username", self.username.get().strip())
            self.password = None
            self.show_main("Active")
            self.request_streak()
            return
        self.login_status.config(
            text=response.get("message", "Login failed."), fg=RED
        )

    def request_streak(self):
        if not self.username:
            return
        self._send_service_request(
            STREAK_REQUEST, STREAK_RESPONSE,
            ["command=GET_STREAK", f"user={self.username}"],
            self.handle_streak_response
        )

    def handle_streak_response(self, response):
        if self.streak_label is None or not self.streak_label.winfo_exists():
            return
        streak = response.get("current_streak", "0")
        self.streak_label.config(text=f"Streak: {streak} days")

    def poll_reminder_response(self):
        if REMINDER_RESPONSE.exists():
            try:
                message = REMINDER_RESPONSE.read_text(encoding="utf-8").strip()
                REMINDER_RESPONSE.unlink()
            except OSError:
                message = ""
            if message.startswith("ALERT"):
                messagebox.showinfo("Session Reminder", "Time to start today's session!")
        self.after(500, self.poll_reminder_response)

    # ---------- Main shell ----------

    def show_main(self, tab="Active"):
        self.clear()
        self.current_page = tab.lower()

        page = tk.Frame(self.root_container, bg=PANEL)
        page.pack(fill="both", expand=True)
        self._draw_background(page)

        header = tk.Frame(page, bg="#151313", height=180)
        header.place(x=0, y=0, relwidth=1, height=180)
        self.title_label(header).place(x=85, y=42)

        search = tk.Entry(header, textvariable=self.search_var,
                          font=("Arial", 14), width=18)
        search.place(x=734, y=21, height=35)
        search.bind("<Return>", lambda _e: self.search_game())

        self.make_button(
            header, "⚙", self.show_settings,
            bg=WHITE, font=("Arial", 24), width=2
        ).place(x=946, y=20, height=50)

        # Tabs
        tabs = [("Active", 40), ("Paused", 260), ("History", 480),
                ("Collection", 700)]
        for label, x in tabs:
            selected = tab.lower() == label.lower()
            b = self.make_button(
                page, label, lambda name=label: self.show_main(name),
                bg=WHITE if selected else TAB_BLUE,
                font=("Arial", 16), width=12
            )
            b.place(x=x, y=138, width=210, height=42)

        self.make_button(page, "+", self.show_add_game,
                         bg=TAB_BLUE, font=("Arial", 25), width=2).place(
                             x=918, y=132, height=48)

        self.streak_label = tk.Label(
            page, text="Streak: -- days", bg=PANEL, fg=BLACK,
            font=("Arial", 12, "bold")
        )
        self.streak_label.place(x=760, y=95)

        content = tk.Frame(page, bg=PANEL)
        content.place(x=2, y=180, relwidth=0.996, relheight=0.73)

        if tab == "Active":
            self.build_active(content)
        elif tab == "Paused":
            self.build_paused(content)
        elif tab == "History":
            self.build_history(content)
        else:
            self.build_collection(content)

    def search_game(self):
        query = self.search_var.get().strip()
        if not query:
            return

        exact = next((g for g in self.games if g["title"].lower() == query.lower()), None)
        if exact:
            self.show_game(exact)
            return

        self._send_service_request(
            READ_REQUEST, READ_RESPONSE,
            ["command=SEARCH", f"keyword={query}"],
            lambda response: self.handle_read_search_response(response, query)
        )

    def handle_read_search_response(self, response, query):
        if response.get("status", "").lower() != "success":
            messagebox.showinfo("Search", response.get("message", "Search failed."))
            return
        count = int(response.get("results", "0") or 0)
        matches = []
        for index in range(1, count + 1):
            name = response.get(f"file{index}_name", "")
            if not name:
                continue
            existing = next((g for g in self.games if g["title"].lower() == Path(name).stem.lower()), None)
            if existing:
                matches.append(existing)
            else:
                matches.append({
                    "title": Path(name).stem, "playtime": 0, "status": "Collection",
                    "cover": None, "estimated": "Unknown", "sessions": 0,
                    "started": "", "review": "", "file_path": response.get(f"file{index}_path", "")
                })
        if len(matches) == 1:
            self.show_game(matches[0])
        elif matches:
            self.show_search_results(matches)
        else:
            messagebox.showinfo("Search", f"No game found for '{query}'.")

    def show_search_results(self, matches):
        win = self.popup_base("Search Results", 520, 430)
        tk.Label(win, text="Select a game", bg=WHITE,
                 font=("Arial", 22, "bold")).pack(pady=15)
        for game in matches:
            self.make_button(
                win, game["title"],
                lambda g=game, w=win: (w.destroy(), self.show_game(g)),
                bg=WHITE, font=("Arial", 14)
            ).pack(fill="x", padx=40, pady=6, ipady=7)

    def filtered_games(self, status):
        # The search bar is navigation, not a tab filter.
        return [g for g in self.games if g["status"] == status]

    # ---------- Active / paused / history / collection ----------

    def build_active(self, parent):
        games = self.filtered_games("Active")
        if games:
            self.build_featured_active(parent, games[0], games[1:3])

        y = 278
        for game in games[3:]:
            self.build_simple_row(parent, game, y)
            y += 70

    def build_featured_active(self, parent, main, side):
        big = self.card(parent)
        big.place(x=37, y=30, width=503, height=285)

        self.add_cover(big, main, 25, 18, 110, 160)

        # Foremost game's title sits underneath its cover.
        tk.Label(
            big, text=main["title"], bg=PANEL_DARK, fg="white",
            font=("Arial", 14, "bold"), wraplength=115, justify="center"
        ).place(x=18, y=183, width=125, height=58)

        self.make_button(
            big, self.timer_button_text(main),
            lambda g=main: self.toggle_timer(g),
            bg=GREEN, font=("Arial", 18)
        ).place(x=140, y=18, width=207, height=98)

        self.make_button(
            big, "Beat It!", lambda g=main: self.mark_beaten(g),
            bg=YELLOW, font=("Arial", 16)
        ).place(x=357, y=18, width=140, height=98)

        self.make_button(
            big, "Add Time\n-h-m", lambda g=main: self.add_time(g),
            bg=BLUE, font=("Arial", 18)
        ).place(x=140, y=126, width=207, height=98)

        self.make_button(
            big, "Pause\nPlaythrough",
            lambda g=main: self.pause_game(g),
            bg=RED, font=("Arial", 15)
        ).place(x=357, y=126, width=140, height=98)

        self.timer_indicator(big, 475, 8)

        y = 30
        for game in side:
            c = self.card(parent)
            c.place(x=560, y=y, width=436, height=108)
            self.add_cover(c, game, 8, 10, 65, 88)

            self.make_button(
                c, game["title"], lambda g=game: self.show_game(g),
                bg=WHITE, font=("Arial", 12)
            ).place(x=85, y=8, width=160, height=28)

            tk.Label(
                c, text=fmt_time(game["playtime"]), bg=WHITE,
                font=("Arial", 12), relief="solid", bd=1
            ).place(x=85, y=43, width=160, height=27)

            # Green=start/stop, yellow=beat, blue=add time, red=pause.
            self.mini_action_buttons(c, game, 270, 16)
            self.timer_indicator(c, 407, 8)
            y += 120


    def timer_button_text(self, game):
        if self.timer_running and self.timer_game is game:
            return "ACTIVE\n" + self.live_time_text(game)
        return "Start/Stop\n" + self.live_time_text(game)

    def live_seconds(self, game):
        base_seconds = float(game.get("playtime", 0)) * 60
        if self.timer_running and self.timer_game is game:
            return base_seconds + (time.monotonic() - self.timer_started_at)
        return base_seconds

    def live_minutes(self, game):
        return int(self.live_seconds(game) / 60)

    def live_time_text(self, game):
        return fmt_duration(self.live_seconds(game))

    def mini_action_buttons(self, parent, game, x, y):
        self.make_button(
            parent, "Start/Stop", lambda g=game: self.toggle_timer(g),
            bg=GREEN, font=("Arial", 13)
        ).place(x=x, y=y, width=35, height=35)

        self.make_button(
            parent, "Beat", lambda g=game: self.mark_beaten(g),
            bg=YELLOW, font=("Arial", 13)
        ).place(x=x + 39, y=y, width=35, height=35)

        self.make_button(
            parent, "+", lambda g=game: self.add_time(g),
            bg=BLUE, font=("Arial", 15)
        ).place(x=x + 78, y=y, width=35, height=35)

        self.make_button(
            parent, "Pause", lambda g=game: self.pause_game(g),
            bg=RED, font=("Arial", 13)
        ).place(x=x + 117, y=y, width=35, height=35)

    def build_simple_row(self, parent, game, y):
        c = self.card(parent)
        c.place(x=37, y=y, width=959, height=55)
        self.make_button(
            c, game["title"], lambda g=game: self.show_game(g),
            bg=WHITE, font=("Arial", 14)
        ).place(x=18, y=8, width=330, height=38)
        tk.Label(c, text=fmt_time(game["playtime"]), bg=WHITE,
                 font=("Arial", 14), relief="solid", bd=1).place(
                     x=356, y=8, width=205, height=38)
        self.status_squares(c, 590, 5)

    @staticmethod
    def parse_estimated_minutes(estimated):
        if not estimated:
            return 0
        match = re.fullmatch(
            r"\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*",
            estimated.lower()
        )
        if not match:
            return 0
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        return hours * 60 + minutes

    def time_left(self, game):
        estimated = self.parse_estimated_minutes(game.get("estimated", ""))
        return fmt_time(max(0, estimated - self.live_minutes(game)))

    def build_paused(self, parent):
        games = self.filtered_games("Paused")
        headings = ["Title", "Playtime", "Time Left", "Days Since\nPause"]
        for i, text in enumerate(headings):
            tk.Label(parent, text=text, bg=PANEL, font=("Arial", 13, "bold")
                     ).place(x=40 + i * 230, y=18)

        y = 65
        for game in games:
            c = self.card(parent)
            c.place(x=37, y=y, width=959, height=72)
            tk.Label(c, text=game["title"], bg=WHITE, font=("Arial", 13),
                     relief="solid", bd=1).place(x=18, y=12, width=205, height=45)
            tk.Label(c, text=fmt_time(game["playtime"]), bg=WHITE,
                     font=("Arial", 13), relief="solid", bd=1).place(
                         x=238, y=12, width=150, height=45)
            tk.Label(c, text=self.time_left(game), bg=WHITE, font=("Arial", 13),
                     relief="solid", bd=1).place(x=400, y=12, width=150, height=45)
            tk.Label(c, text=f'{game.get("days_paused", 0)} Days Ago',
                     bg=WHITE, font=("Arial", 13), relief="solid", bd=1).place(
                         x=565, y=12, width=170, height=45)
            self.make_button(
                c, "Resume",
                lambda g=game: self.resume_game(g),
                bg=GREEN, font=("Arial", 12)
            ).place(x=760, y=12, width=90, height=45)
            self.make_button(
                c, "Open",
                lambda g=game: self.show_game(g),
                bg=YELLOW, font=("Arial", 12)
            ).place(x=860, y=12, width=80, height=45)
            y += 82

    def build_history(self, parent):
        games = self.filtered_games("History")
        for i, game in enumerate(games):
            x = 37 + (i % 4) * 240
            y = 30 + (i // 4) * 180
            c = self.card(parent)
            c.place(x=x, y=y, width=220, height=155)
            self.add_cover(c, game, 10, 10, 62, 85)
            tk.Label(c, text=self.format_title(game["title"], 19),
                     bg=WHITE, font=("Arial", 12), relief="solid", bd=1).place(
                         x=82, y=12, width=125, height=34)
            tk.Label(c, text=fmt_time(game["playtime"]), bg=WHITE,
                     font=("Arial", 12), relief="solid", bd=1).place(
                         x=82, y=55, width=125, height=34)
            tk.Label(c, text="Beat!", bg=GREEN, font=("Arial", 12),
                     relief="solid", bd=1).place(x=82, y=100, width=125, height=34)

    def build_collection(self, parent):
        games = self.filtered_games("Collection")
        for i, game in enumerate(games):
            x = 37 + (i % 4) * 240
            y = 30 + (i // 4) * 180
            c = self.card(parent)
            c.place(x=x, y=y, width=220, height=155)
            self.add_cover(c, game, 10, 10, 62, 85)
            self.make_button(
                c, self.format_title(game["title"], 19),
                lambda g=game: self.show_game(g),
                bg=WHITE, font=("Arial", 11)
            ).place(x=82, y=12, width=125, height=34)
            tk.Label(c, text="In Collection", bg=TAB_BLUE,
                     font=("Arial", 11), relief="solid", bd=1).place(
                         x=82, y=55, width=125, height=34)
            self.make_button(
                c, "Start Playthrough",
                lambda g=game: self.start_collection_game(g),
                bg=GREEN, font=("Arial", 10)
            ).place(x=20, y=105, width=187, height=34)

    # ---------- Game page ----------

    def show_game(self, game):
        self.clear()
        self.current_page = "game"

        page = tk.Frame(self.root_container, bg=PANEL)
        page.pack(fill="both", expand=True)
        self._draw_background(page)

        header = tk.Frame(page, bg="#151313", height=180)
        header.place(x=0, y=0, relwidth=1, height=180)
        self.title_label(header).place(x=85, y=42)

        self.make_button(header, "Search", lambda: self.focus_search(),
                         bg=WHITE, font=("Arial", 13)).place(
                             x=735, y=21, width=185, height=35)
        self.make_button(header, "⚙", self.show_settings,
                         bg=WHITE, font=("Arial", 24), width=2).place(
                             x=946, y=20, height=50)

        self.make_button(page, "← Back", lambda: self.show_main("Active"),
                         bg=TAB_BLUE, font=("Arial", 13)).place(
                             x=40, y=135, width=120, height=40)

        body = tk.Frame(page, bg=PANEL)
        body.place(x=2, y=180, relwidth=0.996, relheight=0.73)

        self.add_cover(body, game, 45, 35, 190, 260)
        tk.Label(body, text=game["title"], bg=PANEL, font=("Arial", 28, "bold")
                 ).place(x=270, y=38)

        self.make_button(
            body, "Basic Analytics",
            lambda: None, bg=WHITE, font=("Arial", 14)
        ).place(x=270, y=100, width=190, height=40)
        self.make_button(
            body, "History",
            lambda: self.show_game_history(game),
            bg=TAB_BLUE, font=("Arial", 14)
        ).place(x=465, y=100, width=120, height=40)

        analytics = tk.Frame(body, bg=PANEL_DARK, highlightbackground=BORDER,
                             highlightthickness=1)
        analytics.place(x=270, y=155, width=675, height=245)

        fields = [
            ("Rating", "—"),
            ("Time Played", fmt_time(game["playtime"])),
            ("Play Sessions", str(game["sessions"])),
            ("Started", game["started"] or "Not started"),
            ("Beat?", "Y" if game["status"] == "History" else "N"),
        ]
        for i, (label, value) in enumerate(fields):
            x = 20 + (i % 3) * 215
            y = 20 + (i // 3) * 85
            tk.Label(analytics, text=label, bg=PANEL_DARK, fg="white",
                     font=("Arial", 12, "bold")).place(x=x, y=y)
            tk.Label(analytics, text=value, bg=WHITE, font=("Arial", 14),
                     relief="solid", bd=1).place(x=x, y=y + 25, width=185, height=38)

        if game.get("review"):
            tk.Label(body, text=game["review"], bg=PANEL, font=("Arial", 13),
                     wraplength=600, justify="left").place(x=270, y=420)

    @staticmethod
    def show_game_history(game):
        messagebox.showinfo(
            "History",
            f"{game['title']}\n\n"
            f"Sessions: {game['sessions']}\n"
            f"Playtime: {fmt_time(game['playtime'])}\n"
            f"Started: {game['started'] or 'Not started'}"
        )

    # ---------- Month / statistics page ----------

    def show_month(self):
        self.clear()
        page = tk.Frame(self.root_container, bg=PANEL)
        page.pack(fill="both", expand=True)
        self._draw_background(page)

        header = tk.Frame(page, bg="#151313", height=180)
        header.place(x=0, y=0, relwidth=1, height=180)
        self.title_label(header).place(x=85, y=42)
        self.make_button(header, "Search", lambda: None,
                         bg=WHITE, font=("Arial", 13)).place(
                             x=735, y=21, width=185, height=35)
        self.make_button(header, "⚙", self.show_settings,
                         bg=WHITE, font=("Arial", 24), width=2).place(
                             x=946, y=20, height=50)

        body = tk.Frame(page, bg=PANEL)
        body.place(x=2, y=180, relwidth=0.996, relheight=0.73)

        tk.Label(body, text="August", bg=PANEL, font=("Arial", 26, "bold")
                 ).place(x=45, y=25)

        stats = [
            ("Games Played", "13"),
            ("Games Beaten", "5"),
            ("Hours Played", "67h34m"),
            ("Most Hours in 1 Day", "10h06m"),
            ("Longest Streak", "16 Days"),
        ]
        for i, (label, value) in enumerate(stats):
            x = 45 + (i % 3) * 300
            y = 75 + (i // 3) * 95
            c = self.card(body)
            c.place(x=x, y=y, width=270, height=80)
            tk.Label(c, text=label, bg=PANEL_DARK, fg="white",
                     font=("Arial", 12)).place(x=10, y=10)
            tk.Label(c, text=value, bg=WHITE, font=("Arial", 18),
                     relief="solid", bd=1).place(x=10, y=36, width=240, height=34)

        chart = self.card(body)
        chart.place(x=45, y=285, width=510, height=210)
        tk.Label(chart, text="Current Month Activity By Game",
                 bg=PANEL_DARK, fg="white", font=("Arial", 14, "bold")).pack(
                     pady=10)
        self.draw_pie_chart(chart)

        chart2 = self.card(body)
        chart2.place(x=580, y=285, width=416, height=210)
        tk.Label(chart2, text="Last Three Months Total Playtime",
                 bg=PANEL_DARK, fg="white", font=("Arial", 14, "bold")).pack(
                     pady=10)
        self.draw_bar_chart(chart2)

    @staticmethod
    def draw_pie_chart(parent):
        canvas = tk.Canvas(parent, bg=PANEL_DARK, highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=20, pady=5)
        values = [35, 25, 18, 12, 10]
        start = 0
        colors = [GREEN, YELLOW, BLUE, RED, "#8f8f8f"]
        for value, color in zip(values, colors):
            extent = 360 * value / 100
            canvas.create_arc(85, 15, 235, 165, start=start, extent=extent,
                              fill=color, outline=BLACK)
            start += extent

    @staticmethod
    def draw_bar_chart(parent):
        canvas = tk.Canvas(parent, bg=PANEL_DARK, highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=20, pady=5)
        values = [56, 20, 47]
        labels = ["June", "July", "August"]
        max_value = max(values)
        for i, (value, label) in enumerate(zip(values, labels)):
            x = 40 + i * 115
            h = 120 * value / max_value
            canvas.create_rectangle(x, 155 - h, x + 70, 155,
                                    fill=[GREEN, YELLOW, BLUE][i], outline=BLACK)
            canvas.create_text(x + 35, 172, text=label, fill="white",
                               font=("Arial", 10))
            canvas.create_text(x + 35, 145 - h, text=f"{value}h",
                               fill="white", font=("Arial", 10))

    # ---------- Settings / add-game popups ----------

    def popup_base(self, title, width=560, height=430):
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry(f"{width}x{height}")
        win.configure(bg=WHITE)
        win.transient(self)
        win.grab_set()
        return win

    def show_settings(self):
        win = self.popup_base("Settings", 560, 430)
        tk.Label(win, text="settings", bg=WHITE, font=("Arial", 25)
                 ).pack(fill="x", pady=(15, 10))
        self.make_button(win, "Change Theme",
                         lambda: messagebox.showinfo("Theme", "Theme options can be connected here."),
                         bg=WHITE, font=("Arial", 15)).pack(fill="x", padx=35, pady=10, ipady=8)
        self.make_button(win, "Custom Theme",
                         lambda: messagebox.showinfo("Custom Theme", "Custom theme editor placeholder."),
                         bg=WHITE, font=("Arial", 15)).pack(fill="x", padx=35, pady=10, ipady=8)
        self.make_button(win, "Customize Chart Details",
                         lambda: messagebox.showinfo("Charts", "Chart customization placeholder."),
                         bg=WHITE, font=("Arial", 15)).pack(fill="x", padx=35, pady=10, ipady=8)
        self.make_button(win, "Month Statistics", self.show_month,
                         bg=TAB_BLUE, font=("Arial", 15)).pack(
                             fill="x", padx=35, pady=10, ipady=8)
        self.make_button(win, "Session Reminder", self.show_reminder_settings,
                         bg=TAB_BLUE, font=("Arial", 15)).pack(
                             fill="x", padx=35, pady=10, ipady=8)
        self.make_button(win, "Log Out",
                         lambda: (win.destroy(), self.show_login()),
                         bg=RED, font=("Arial", 15)).pack(
                             fill="x", padx=35, pady=10, ipady=8)

    @staticmethod
    def clear_reminder():
        try:
            REMINDER_REQUEST.write_text("CLEAR\n", encoding="utf-8")
        except OSError:
            pass

    def set_reminder(self, time_value):
        try:
            REMINDER_REQUEST.write_text(f"SET_TIME\n{time_value}\n", encoding="utf-8")
        except OSError:
            pass

    def show_reminder_settings(self):
        win = self.popup_base("Session Reminder", 360, 250)
        tk.Label(win, text="Reminder Time (HH:MM)", bg=WHITE, font=("Arial", 13)).pack(pady=20)
        entry = tk.Entry(win, font=("Arial", 16), justify="center")
        entry.insert(0, "18:00")
        entry.pack()
        self.make_button(win, "Set Reminder", lambda: (self.set_reminder(entry.get().strip()), win.destroy()), bg=GREEN).pack(pady=15, ipadx=20, ipady=6)
        self.make_button(win, "Clear Today's Reminder", lambda: (self.clear_reminder(), win.destroy()), bg=RED).pack(ipadx=10, ipady=6)

    def search_database_for_add(self, search_entry, title_entry, estimated_entry):
        query = search_entry.get().strip()
        if not query:
            messagebox.showwarning("Search Database", "Enter a game title.")
            return
        self._send_service_request(
            READ_REQUEST, READ_RESPONSE,
            ["command=SEARCH", f"keyword={query}"],
            lambda response: self.handle_add_search_response(
                response, title_entry, estimated_entry
            )
        )

    def handle_add_search_response(self, response, title_entry, estimated_entry):
        if response.get("status", "").lower() != "success":
            messagebox.showinfo("Search Database", response.get("message", "Search failed."))
            return
        count = int(response.get("results", "0") or 0)
        if count == 0:
            messagebox.showinfo("Search Database", "No matching files found.")
            return
        name = response.get("file1_name", "")
        title_entry.delete(0, tk.END)
        title_entry.insert(0, Path(name).stem)
        messagebox.showinfo("Search Database", f"Found: {name}")

    def show_add_game(self):
        win = self.popup_base("Add to Collection", 600, 500)
        tk.Label(win, text="add to collection", bg=WHITE,
                 font=("Arial", 25)).pack(fill="x", pady=(15, 10))

        tk.Label(win, text="Search Database", bg=WHITE,
                 font=("Arial", 14)).pack(pady=(10, 2))
        search = tk.Entry(win, font=("Arial", 14))
        search.pack(fill="x", padx=45, ipady=7)

        tk.Label(win, text="Game Title", bg=WHITE,
                 font=("Arial", 14)).pack(pady=(15, 2))
        title = tk.Entry(win, font=("Arial", 14))
        title.pack(fill="x", padx=45, ipady=7)

        tk.Label(win, text="Estimated Playtime", bg=WHITE,
                 font=("Arial", 14)).pack(pady=(15, 2))
        estimated = tk.Entry(win, font=("Arial", 14))
        estimated.pack(fill="x", padx=45, ipady=7)

        row = tk.Frame(win, bg=WHITE)
        row.pack(fill="x", padx=45, pady=20)
        self.make_button(
            row, "Search Database",
            lambda: self.search_database_for_add(search, title, estimated),
            bg=WHITE, font=("Arial", 13)
        ).pack(side="left", expand=True, fill="x", padx=(0, 5), ipady=8)

        def search_database_for_add():
            self.search_database_for_add(search, title, estimated)

        def add():
            name = title.get().strip() or search.get().strip()
            if not name:
                messagebox.showwarning("Add Game", "Enter a game title.")
                return
            self.games.append({
                "title": name,
                "playtime": 0,
                "status": "Collection",
                "cover": None,
                "estimated": estimated.get().strip() or "Unknown",
                "sessions": 0,
                "started": "",
                "review": "",
            })
            win.destroy()
            self.save_current_state()
            self.show_main("Collection")

        self.make_button(row, "Add Game", add, bg=GREEN,
                         font=("Arial", 13)).pack(side="left", expand=True,
                                                 fill="x", padx=(5, 0), ipady=8)

    # ---------- Timer / game state ----------

    def toggle_timer(self, game):
        if self.timer_running and self.timer_game is game:
            self.stop_timer()
        else:
            self.start_timer(game)

    def start_timer(self, game):
        if self.timer_running:
            self.stop_timer()
        self.timer_game = game
        self.timer_running = True
        self.timer_started_at = time.monotonic()
        game["status"] = "Active"
        if self.username:
            self._send_service_request(
                STREAK_REQUEST, STREAK_RESPONSE,
                ["command=START_SESSION", f"user={self.username}"],
                self.handle_streak_response
            )
        self._timer_tick()

    def stop_timer(self):
        if self.timer_running and self.timer_game is not None:
            elapsed_seconds = time.monotonic() - self.timer_started_at
            if elapsed_seconds > 0:
                self.timer_game["playtime"] += elapsed_seconds / 60
                self.save_current_state()
        self.timer_running = False
        self.timer_game = None
        if self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None

    def _timer_tick(self):
        if self.timer_running and self.timer_game is not None:
            if self.current_page == "active":
                self.show_main("Active")
            self.timer_job = self.after(50, self._timer_tick)

    def add_time(self, game):
        win = self.popup_base("Add Time", 320, 210)
        tk.Label(win, text="Minutes to add", bg=WHITE,
                 font=("Arial", 13)).pack(pady=15)
        entry = tk.Entry(win, font=("Arial", 16), justify="center")
        entry.insert(0, "30")
        entry.pack()

        def add():
            try:
                mins = int(entry.get())
                if mins < 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Add Time", "Enter a non-negative integer.")
                return
            game["playtime"] += mins
            win.destroy()
            self.save_current_state()
            self.show_main("Active")

        self.make_button(win, "Add", add, bg=GREEN,
                         font=("Arial", 13)).pack(pady=15, ipadx=25, ipady=5)

    def pause_game(self, game):
        game["status"] = "Paused"
        game["days_paused"] = 0
        if self.timer_game is game:
            self.stop_timer()
        self.save_current_state()
        self.show_main("Paused")

    def resume_game(self, game):
        game["status"] = "Active"
        self.save_current_state()
        self.show_main("Active")

    def mark_beaten(self, game):
        game["status"] = "History"
        if self.timer_game is game:
            self.stop_timer()
        self.save_current_state()
        self.show_main("History")

    def start_collection_game(self, game):
        game["status"] = "Active"
        game["started"] = time.strftime("%m/%d/%Y")
        self.save_current_state()
        self.show_main("Active")

    def add_cover(self, parent, game, x, y, w, h):
        path = ASSET_DIR / game["cover"] if game.get("cover") else None
        if Image is not None and path and path.exists():
            key = (str(path), w, h)
            if key not in self.cover_cache:
                img = Image.open(path).convert("RGB")
                img.thumbnail((w, h))
                self.cover_cache[key] = ImageTk.PhotoImage(img)
            label = tk.Label(parent, image=self.cover_cache[key], bg=WHITE,
                             bd=1, relief="solid")
        else:
            label = tk.Label(
                parent, text="ART", bg="#c9c9c9", fg=BLACK,
                font=("Arial", 16, "bold"), bd=1, relief="solid"
            )
        label.place(x=x, y=y, width=w, height=h)

    @staticmethod
    def status_squares(parent, x, y):
        for i, color in enumerate([GREEN, YELLOW, BLUE, RED]):
            tk.Label(parent, bg=color, bd=1, relief="solid").place(
                x=x + i * 70, y=y, width=50, height=40
            )

    def focus_search(self):
        self.show_main("Active")


if __name__ == "__main__":
    window = GameThroughApp()
    window.mainloop()
