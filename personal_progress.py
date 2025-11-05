from __future__ import annotations
import sqlite3, os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Zagreb")
except Exception:
    TZ = None

DB_PATH = "progress.db"


@dataclass
class Task:
    id: Optional[int]
    name: str
    points: float
    description: str
    ts: str


def _now_iso() -> str:
    if TZ:
        return datetime.now(TZ).isoformat(timespec="seconds")
    return datetime.now().isoformat(timespec="seconds")


def init_db(path: str = DB_PATH) -> None:
    conn = sqlite3.connect(path)
    try:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                points REAL NOT NULL,
                description TEXT,
                ts TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def add_task(name: str, points: float, description: str = "", ts: Optional[str] = None, path: str = DB_PATH) -> int:
    if ts is None:
        ts = _now_iso()
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tasks(name, points, description, ts) VALUES (?, ?, ?, ?)",
            (name, points, description, ts),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_task(task_id: int, path: str = DB_PATH) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        conn.commit()
    finally:
        conn.close()


def list_tasks(path: str = DB_PATH) -> List[Task]:
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute("SELECT id,name,points,description,ts FROM tasks ORDER BY ts DESC").fetchall()
        return [Task(*r) for r in rows]
    finally:
        conn.close()


def total_points(path: str = DB_PATH) -> float:
    conn = sqlite3.connect(path)
    try:
        (s,) = conn.execute("SELECT COALESCE(SUM(points),0) FROM tasks").fetchone()
        return float(s or 0.0)
    finally:
        conn.close()


# --- PREDEFINIRANI ZADACI ---

PREDEFINED = [
    ("Izgradnja/kupovina stana/kuće", 350.0),
    ("Rješen diplomski", 5.0),
    ("Dobijen posao", 15.0),
    ("Plaća > 2400€ neto", 50.0),
    ("Kupovina montažne kućice", 100.0),
    ("Putovanje u novu državu", 5.0),
    ("Kupovina broda", 30.0),
    ("Prodaja ostvarena na OPG-u", 0.5),
    ("Kupovina automobila", 20.0),
    ("Selidba od roditelja", 40.0),
]

def add_predefined(name: str, description: str = "", path: str = DB_PATH) -> int:
    mapping = {n: p for n, p in PREDEFINED}
    if name not in mapping:
        raise ValueError(f"Nepoznat predefinirani zadatak: {name}")
    return add_task(name, mapping[name], description, path=path)


def add_investment(amount_eur: float, description: str = "", path: str = DB_PATH) -> int:
    """Dodaje zadatak za ulaganje u dionice – 1 bod na svakih 1000 €."""
    points = amount_eur / 1000.0
    name = f"Uloženo u dionice {amount_eur:,.0f} €".replace(",", ".")
    return add_task(name, points, description, path=path)

# --- TO-DO LISTA ---
def init_todo_db(path: str = DB_PATH) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER DEFAULT 0,
                ts_created TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def add_todo(title: str, path: str = DB_PATH) -> int:
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO todos (title, done, ts_created) VALUES (?, 0, ?)", (title, _now_iso()))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_todos(path: str = DB_PATH):
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute("SELECT id,title,done,ts_created FROM todos ORDER BY id DESC").fetchall()
        return [{"id": r[0], "title": r[1], "done": bool(r[2]), "ts": r[3]} for r in rows]
    finally:
        conn.close()


def mark_todo_done(todo_id: int, path: str = DB_PATH):
    """Označi dovršen i doda dnevni zadatak s opisom."""
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT title FROM todos WHERE id=?", (todo_id,))
        row = cur.fetchone()
        title = row[0] if row else f"To-Do {todo_id}"
        cur.execute("UPDATE todos SET done=1 WHERE id=?", (todo_id,))
        conn.commit()
    finally:
        conn.close()
    add_task("Dnevni zadatak", 0.2, title, path=path)


def delete_todo(todo_id: int, path: str = DB_PATH):
    conn = sqlite3.connect(path)
    try:
        conn.execute("DELETE FROM todos WHERE id=?", (todo_id,))
        conn.commit()
    finally:
        conn.close()


def reset_completed_todos(path: str = DB_PATH):
    """Automatski briše sve dovršene to-do zadatke starije od 1 dana."""
    conn = sqlite3.connect(path)
    try:
        cutoff = (datetime.now(TZ) - timedelta(days=1)).isoformat(timespec="seconds")
        conn.execute("DELETE FROM todos WHERE done=1 AND ts_created < ?", (cutoff,))
        conn.commit()
    finally:
        conn.close()


# --- RESET ---
def reset_all_data(path: str = DB_PATH):
    if os.path.exists(path):
        os.remove(path)
    init_db(path)
    init_todo_db(path)


# --- STATISTIKA / KALENDAR ---
def points_per_day(path: str = DB_PATH):
    """Vraća dict {datum: suma_bodova}"""
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT substr(ts,1,10) as day, SUM(points)
            FROM tasks
            GROUP BY day
            ORDER BY day
        """)
        return {r[0]: r[1] for r in cur.fetchall()}
    finally:
        conn.close()


def streak_days(path: str = DB_PATH) -> int:
    """Računa koliko dana zaredom imaš barem jedan zadatak."""
    days = list(points_per_day(path).keys())
    if not days:
        return 0
    days = [datetime.fromisoformat(d) for d in days]
    days.sort(reverse=True)
    streak = 1
    for i in range(1, len(days)):
        if (days[i - 1] - days[i]).days == 1:
            streak += 1
        else:
            break
    return streak