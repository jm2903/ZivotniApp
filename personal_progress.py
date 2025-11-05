from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
from collections import defaultdict
from supabase_handler import supabase

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Zagreb")
except Exception:
    TZ = None


# =====================
#   OSNOVNE POMOĆNE
# =====================

def _now_iso() -> str:
    if TZ:
        return datetime.now(TZ).isoformat(timespec="seconds")
    return datetime.now().isoformat(timespec="seconds")


# =====================
#   MODEL
# =====================

@dataclass
class Task:
    id: Optional[int]
    task: str
    points: float
    note: str
    date: str


# =====================
#   PROGRESS (ZADACI)
# =====================

def add_task(task: str, points: float, description: str = ""):
    """Dodaje zadatak u Supabase."""
    data = {
        "date": _now_iso()[:10],
        "task": task,
        "points": points,
        "note": description,
    }
    try:
        supabase.table("progress").insert(data).execute()
    except Exception as e:
        print(f"[Supabase] Insert error: {e}")


def list_tasks() -> List[Task]:
    """Vraća sve zadatke iz Supabase tablice 'progress'."""
    try:
        res = supabase.table("progress").select("*").order("id", desc=False).execute()
        return res.data or []
    except Exception as e:
        print(f"[Supabase] list_tasks error: {e}")
        return []


def delete_task(task_id: int) -> None:
    """Briše zadatak iz Supabase."""
    try:
        supabase.table("progress").delete().eq("id", int(task_id)).execute()
    except Exception as e:
        print(f"[Supabase] Delete error: {e}")


def total_points() -> float:
    """Računa ukupne bodove iz Supabase."""
    try:
        res = supabase.table("progress").select("points").execute()
        return round(sum(float(r.get("points") or 0) for r in (res.data or [])), 2)
    except Exception as e:
        print(f"[Supabase] total_points error: {e}")
        return 0.0


# =====================
#   PREDEFINIRANI / POSEBNI ZADACI
# =====================

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


def add_predefined(name: str, description: str = ""):
    mapping = {n: p for n, p in PREDEFINED}
    if name not in mapping:
        raise ValueError(f"Nepoznat predefinirani zadatak: {name}")
    add_task(name, mapping[name], description)


def add_investment(amount_eur: float, description: str = ""):
    """Dodaje zadatak za ulaganje u dionice – 1 bod na svakih 1000 €."""
    points = amount_eur / 1000.0
    name = f"Uloženo u dionice {amount_eur:,.0f} €".replace(",", ".")
    add_task(name, points, description)


# =====================
#   TO-DO LISTA (u Supabase)
# =====================

def add_todo(title: str):
    """Dodaje To-Do zadatak u Supabase tablicu 'todos'."""
    try:
        supabase.table("todos").insert({
            "title": title,
            "done": False,
            "ts_created": _now_iso()
        }).execute()
    except Exception as e:
        print(f"[Supabase] add_todo error: {e}")


def list_todos():
    """Dohvaća sve To-Do zadatke iz Supabase."""
    try:
        res = supabase.table("todos").select("*").order("id", desc=True).execute()
        return res.data or []
    except Exception as e:
        print(f"[Supabase] list_todos error: {e}")
        return []


def mark_todo_done(todo_id: int):
    """Označi zadatak dovršenim i dodaj 0.2 boda u progress."""
    try:
        # Dohvati naslov
        res = supabase.table("todos").select("title").eq("id", int(todo_id)).execute()
        title = res.data[0]["title"] if res.data else f"To-Do {todo_id}"

        # Označi dovršenim
        supabase.table("todos").update({"done": True}).eq("id", int(todo_id)).execute()

        # Dodaj bodove u progress
        add_task("Dnevni zadatak", 0.2, title)
    except Exception as e:
        print(f"[Supabase] mark_todo_done error: {e}")


def delete_todo(todo_id: int):
    """Briše To-Do zadatak."""
    try:
        supabase.table("todos").delete().eq("id", int(todo_id)).execute()
    except Exception as e:
        print(f"[Supabase] delete_todo error: {e}")


def reset_completed_todos():
    """Automatski briše To-Do zadatke starije od 1 dana koji su označeni kao dovršeni."""
    try:
        cutoff = (datetime.now(TZ) - timedelta(days=1)).isoformat(timespec="seconds")
        res = supabase.table("todos").select("id,ts_created").execute()
        for todo in (res.data or []):
            if todo.get("done") and todo.get("ts_created") < cutoff:
                supabase.table("todos").delete().eq("id", todo["id"]).execute()
    except Exception as e:
        print(f"[Supabase] reset_completed_todos error: {e}")


# =====================
#   STATISTIKA
# =====================

def points_per_day() -> dict:
    """Vraća dict {datum: suma_bodova} iz Supabase tablice 'progress'."""
    per_day = defaultdict(float)
    try:
        res = supabase.table("progress").select("date,points").execute()
        for r in (res.data or []):
            d = (r.get("date") or "")[:10]
            if not d:
                continue
            per_day[d] += float(r.get("points") or 0)
    except Exception as e:
        print(f"[Supabase] points_per_day error: {e}")
        return {}
    return dict(sorted(per_day.items(), key=lambda x: x[0]))


def streak_days() -> int:
    """Računa koliko dana zaredom imaš barem jedan zadatak (iz Supabase)."""
    days = list(points_per_day().keys())
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