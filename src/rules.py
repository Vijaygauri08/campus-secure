"""Access-decision engine."""
from . import database as db


def decide(plate, valid_format):
    """Return (decision, message). Decisions: ALLOW, ALERT, DENY, REVIEW."""
    if not plate or not valid_format:
        return "REVIEW", "Plate unreadable / invalid format - guard verification needed."
    v = db.get_vehicle(plate)
    if v is None:
        return "DENY", "Unregistered vehicle - direct to visitor desk."
    if v["category"] == "blacklist":
        return "ALERT", f"BLACKLISTED vehicle ({v['owner']}) - notify security!"
    return "ALLOW", f"{v['category'].title()} vehicle - {v['owner']}."
