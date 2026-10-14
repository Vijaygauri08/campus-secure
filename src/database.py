"""SQLite storage: registered vehicles + entry/exit logs."""
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "campus_secure.db"
CATEGORIES = ["staff", "student", "visitor", "blacklist"]


def _conn():
    return sqlite3.connect(DB_PATH)


def init():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS vehicles(
            plate TEXT PRIMARY KEY, owner TEXT, category TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT, plate TEXT, ts TEXT,
            event TEXT, gate TEXT, decision TEXT)""")


def add_vehicle(plate, owner, category):
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO vehicles VALUES(?,?,?)", (plate, owner, category))


def get_vehicle(plate):
    with _conn() as c:
        r = c.execute("SELECT plate, owner, category FROM vehicles WHERE plate=?", (plate,)).fetchone()
    return dict(zip(("plate", "owner", "category"), r)) if r else None


def all_vehicles():
    with _conn() as c:
        return c.execute("SELECT plate, owner, category FROM vehicles").fetchall()


def next_event(plate):
    """Auto-toggle: if last event was ENTRY, this one is EXIT."""
    with _conn() as c:
        r = c.execute("SELECT event FROM logs WHERE plate=? ORDER BY id DESC LIMIT 1", (plate,)).fetchone()
    return "EXIT" if r and r[0] == "ENTRY" else "ENTRY"


def log_event(plate, event, gate, decision):
    with _conn() as c:
        c.execute("INSERT INTO logs(plate, ts, event, gate, decision) VALUES(?,?,?,?,?)",
                  (plate, datetime.now().isoformat(timespec="seconds"), event, gate, decision))


def recent_logs(limit=200):
    with _conn() as c:
        return c.execute("SELECT ts, plate, event, gate, decision FROM logs ORDER BY id DESC LIMIT ?",
                         (limit,)).fetchall()


def overstaying_visitors(hours=4):
    """Visitors whose latest event is ENTRY and older than `hours`."""
    q = """SELECT l.plate, l.ts FROM logs l
           JOIN (SELECT plate, MAX(id) mid FROM logs GROUP BY plate) m ON l.id = m.mid
           WHERE l.event='ENTRY'"""
    limit = datetime.now() - timedelta(hours=hours)
    with _conn() as c:
        rows = c.execute(q).fetchall()
    out = []
    for plate, ts in rows:
        v = get_vehicle(plate)
        if v and v["category"] == "visitor" and datetime.fromisoformat(ts) < limit:
            out.append((plate, ts))
    return out
