#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║              PIXELA HABIT TRACKER  —  by You                ║
║  Tracks: Push-ups · Book Reading · English Speaking         ║
║  Built for long-term use (5+ years). All data on Pixela.    ║
╚══════════════════════════════════════════════════════════════╝

FIRST TIME:
  python pixela_tracker.py --setup

DAILY USE:
  python pixela_tracker.py          ← interactive main menu

OTHER COMMANDS:
  python pixela_tracker.py --setup      create account + graphs
  python pixela_tracker.py --log        log a session (morning/evening)
  python pixela_tracker.py --view       view stats & graph URLs
  python pixela_tracker.py --edit       edit/update any past date
  python pixela_tracker.py --history    view recent pixel history
  python pixela_tracker.py --delete     delete a pixel on any date
"""

import requests
import sys
import os
from datetime import datetime, timedelta
from typing import Optional

# ══════════════════════════════════════════════════════════════════
#  ⚙️  CONFIGURATION — edit these before first run
# ══════════════════════════════════════════════════════════════════

USERNAME = "***REMOVED***"      # lowercase letters, numbers, hyphens only
TOKEN    = "my-secret-token-***REMOVED***"  # any string you choose — keep it private

# ── Graph definitions ────────────────────────────────────────────
GRAPHS = {
    "1": {
        "id":      "pushups",
        "name":    "💪 Push-ups",
        "label":   "Push-ups",
        "unit":    "reps",
        "type":    "int",
        "color":   "shibafu",   # green
        "default": 150,
        "note":    "Total reps across both sessions",
    },
    "2": {
        "id":      "reading",
        "name":    "📚 Book Reading",
        "label":   "Reading",
        "unit":    "pages",
        "type":    "int",
        "color":   "sora",      # blue
        "default": 10,
        "note":    "Pages of Atomic Habits (or any book)",
    },
    "3": {
        "id":      "speaking",
        "name":    "🗣️  English Speaking",
        "label":   "Speaking",
        "unit":    "minutes",
        "type":    "int",
        "color":   "ichou",     # yellow-green
        "default": 40,
        "note":    "Minutes of fluency practice",
    },
}

PIXELA_BASE = "https://pixe.la/v1"
HEADERS     = {"X-USER-TOKEN": TOKEN}
TIMEZONE    = "Africa/Kigali"


# ══════════════════════════════════════════════════════════════════
#  🎨  TERMINAL COLORS & UI HELPERS
# ══════════════════════════════════════════════════════════════════

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    GREEN  = "\033[92m"
    BLUE   = "\033[94m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    MAGENTA= "\033[95m"
    WHITE  = "\033[97m"

def bold(s):    return f"{C.BOLD}{s}{C.RESET}"
def green(s):   return f"{C.GREEN}{s}{C.RESET}"
def blue(s):    return f"{C.BLUE}{s}{C.RESET}"
def yellow(s):  return f"{C.YELLOW}{s}{C.RESET}"
def red(s):     return f"{C.RED}{s}{C.RESET}"
def cyan(s):    return f"{C.CYAN}{s}{C.RESET}"
def dim(s):     return f"{C.DIM}{s}{C.RESET}"
def magenta(s): return f"{C.MAGENTA}{s}{C.RESET}"

def divider(char="─", width=58):
    print(dim(char * width))

def header(title: str):
    print()
    divider("═")
    print(f"  {bold(title)}")
    divider("═")

def section(title: str):
    print()
    print(f"  {cyan(title)}")
    divider()

def success(msg: str):
    print(f"  {green('✅')} {msg}")

def error(msg: str):
    print(f"  {red('❌')} {msg}")

def warn(msg: str):
    print(f"  {yellow('⚠️ ')} {msg}")

def info(msg: str):
    print(f"  {blue('ℹ️ ')} {msg}")

def banner():
    print(f"""
{cyan('╔══════════════════════════════════════════════════════════╗')}
{cyan('║')}  {bold('PIXELA HABIT TRACKER')}  {dim('·  Your discipline, visualized')}   {cyan('║')}
{cyan('║')}  {dim('Pushups  ·  Reading  ·  English Speaking')}                {cyan('║')}
{cyan('╚══════════════════════════════════════════════════════════╝')}
  {dim(f"Today: {now_label()}")}
""")


# ══════════════════════════════════════════════════════════════════
#  📅  DATE HELPERS
# ══════════════════════════════════════════════════════════════════

def today_str() -> str:
    return datetime.now().strftime("%Y%m%d")

def yesterday_str() -> str:
    return (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

def now_label() -> str:
    return datetime.now().strftime("%A, %d %B %Y  %H:%M")

def fmt_date(yyyymmdd: str) -> str:
    try:
        return datetime.strptime(yyyymmdd, "%Y%m%d").strftime("%A, %d %B %Y")
    except ValueError:
        return yyyymmdd

def parse_date_input(raw: str) -> Optional[str]:
    """
    Accept many natural formats:
      today / t                → today
      yesterday / y            → yesterday
      -1, -2, -N               → N days ago
      20240115                 → exact yyyyMMdd
      2024-01-15 / 15-01-2024  → with dashes
      15/01/2024               → with slashes
    Returns yyyyMMdd string or None if invalid.
    """
    raw = raw.strip().lower()
    if raw in ("today", "t", ""):
        return today_str()
    if raw in ("yesterday", "y"):
        return yesterday_str()
    if raw.startswith("-") and raw[1:].isdigit():
        n = int(raw[1:])
        return (datetime.now() - timedelta(days=n)).strftime("%Y%m%d")
    # Try various date formats
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y%m%d")
        except ValueError:
            continue
    return None

def prompt_date(prompt_text: str = "Date", default: str = "today") -> str:
    """Prompt user for a date, return yyyyMMdd."""
    hint = dim("today / yesterday / -1 / 20250115 / 15-01-2025")
    while True:
        raw = input(f"\n  {prompt_text} [{default}]: ").strip()
        if raw == "":
            raw = default
        result = parse_date_input(raw)
        if result:
            label = fmt_date(result)
            print(f"  {dim(f'→ {label}')}")
            return result
        error(f"Could not parse '{raw}'. Try: today, yesterday, -2, 20250115")


# ══════════════════════════════════════════════════════════════════
#  🌐  PIXELA API LAYER
#
#  NOTE: On the free Pixela plan, GET pixel endpoints are restricted
#  to Supporters only. All write operations (POST, PUT, DELETE) work
#  on the free plan. We use safe_json() throughout to handle any
#  non-JSON or malformed responses without crashing.
# ══════════════════════════════════════════════════════════════════

def safe_json(response: requests.Response) -> dict:
    """
    Safely parse a Pixela API response to dict.
    Pixela sometimes returns plain text (e.g. 'null') or empty bodies
    on certain endpoints, which causes requests' .json() to raise
    JSONDecodeError. This wrapper handles that gracefully.
    """
    try:
        return response.json()
    except Exception:
        # If we got a 2xx status, treat it as success with no body
        if response.ok:
            return {"isSuccess": True, "message": response.text.strip()}
        return {"isSuccess": False, "message": response.text.strip() or "Unknown error"}


def api_create_user() -> dict:
    return safe_json(requests.post(
        f"{PIXELA_BASE}/users",
        json={
            "token":               TOKEN,
            "username":            USERNAME,
            "agreeTermsOfService": "yes",
            "notMinor":            "yes",
        },
    ))

def api_create_graph(g: dict) -> dict:
    return safe_json(requests.post(
        f"{PIXELA_BASE}/users/{USERNAME}/graphs",
        headers=HEADERS,
        json={
            "id":             g["id"],
            "name":           g["label"],
            "unit":           g["unit"],
            "type":           g["type"],
            "color":          g["color"],
            "timezone":       TIMEZONE,
            "selfSufficient": "none",
        },
    ))

def api_get_pixel(graph_id: str, date: str) -> dict:
    """
    GET a single pixel — Supporter-only on free plan.
    Returns the response dict; caller should check for supporter error.
    """
    return safe_json(requests.get(
        f"{PIXELA_BASE}/users/{USERNAME}/graphs/{graph_id}/{date}",
        headers=HEADERS,
    ))

def api_post_pixel(graph_id: str, date: str, quantity: int) -> dict:
    return safe_json(requests.post(
        f"{PIXELA_BASE}/users/{USERNAME}/graphs/{graph_id}",
        headers=HEADERS,
        json={"date": date, "quantity": str(quantity)},
    ))
    
def api_add_pixel(graph_id: str, date: str, quantity: int) -> dict:
    """PUT /add — adds quantity to existing pixel, or creates it. Free plan. No GET needed."""
    return safe_json(requests.put(
        f"{PIXELA_BASE}/users/{USERNAME}/graphs/{graph_id}/{date}/add",
        headers=HEADERS,
        json={"quantity": str(quantity)},
    ))

def api_put_pixel(graph_id: str, date: str, quantity: int) -> dict:
    return safe_json(requests.put(
        f"{PIXELA_BASE}/users/{USERNAME}/graphs/{graph_id}/pixels/{date}",
        headers=HEADERS,
        json={"quantity": str(quantity)},
    ))

def api_delete_pixel(graph_id: str, date: str) -> dict:
    return safe_json(requests.delete(
        f"{PIXELA_BASE}/users/{USERNAME}/graphs/{graph_id}/pixels/{date}",
        headers=HEADERS,
    ))

def api_get_pixels(graph_id: str, from_date: str, to_date: str) -> dict:
    return safe_json(requests.get(
        f"{PIXELA_BASE}/users/{USERNAME}/graphs/{graph_id}/pixels",
        headers=HEADERS,
        params={"from": from_date, "to": to_date},
    ))

def api_get_graph_stats(graph_id: str) -> dict:
    return safe_json(requests.get(
        f"{PIXELA_BASE}/users/{USERNAME}/graphs/{graph_id}/stats",
        headers=HEADERS,
    ))

def api_list_graphs() -> dict:
    return safe_json(requests.get(
        f"{PIXELA_BASE}/users/{USERNAME}/graphs",
        headers=HEADERS,
    ))

def graph_url(graph_id: str) -> str:
    return f"https://pixe.la/v1/users/{USERNAME}/graphs/{graph_id}.html"

def graph_svg_url(graph_id: str) -> str:
    return f"https://pixe.la/v1/users/{USERNAME}/graphs/{graph_id}"

def is_supporter_error(res: dict) -> bool:
    """Check if the API returned a Supporter-only restriction error."""
    msg = res.get("message", "").lower()
    return "supporter" in msg


# ══════════════════════════════════════════════════════════════════
#  🔢  SMART PIXEL UPSERT
#
#  Free-plan compatible strategy:
#
#  mode='add' (logging sessions):
#    1. Try POST  → succeeds if pixel doesn't exist yet today
#    2. If POST fails with "already exist", try PUT with the
#       new quantity alone (we can't read the old value on free plan,
#       so we note that the total was overwritten, not accumulated)
#
#  mode='set' (editing):
#    1. Try PUT  → succeeds if pixel exists
#    2. If PUT fails, try POST (pixel didn't exist yet)
#
#  For true accumulation across sessions on the free plan, consider
#  upgrading to Pixela Supporter (~$2/mo) to unlock GET pixel.
# ══════════════════════════════════════════════════════════════════

def upsert_pixel(graph_id: str, date: str, quantity: int, mode: str = "add") -> tuple[bool, str]:
    """
    mode='add'  → add quantity to existing pixel (used when logging sessions)
    mode='set'  → overwrite pixel with exact quantity (used when editing)
    Returns (success: bool, message: str)
    """
    if mode == "set":
        # Try PUT first (update existing pixel)
        res = api_put_pixel(graph_id, date, quantity)
        if res.get("isSuccess"):
            return True, f"Set to {quantity}"
        # PUT failed — pixel may not exist yet; try POST (create)
        res = api_post_pixel(graph_id, date, quantity)
        if res.get("isSuccess"):
            return True, f"Created with {quantity}"
        return False, res.get("message", "Unknown error")

    else:  # mode == "add"
        # Use the /add endpoint — works on free plan, auto-creates if missing,
        # and properly accumulates across morning + evening sessions.
        res = api_add_pixel(graph_id, date, quantity)
        if res.get("isSuccess"):
            return True, f"Added {quantity} (total accumulated on Pixela)"
        return False, res.get("message", "Unknown error")


# ══════════════════════════════════════════════════════════════════
#  📝  INPUT HELPERS
# ══════════════════════════════════════════════════════════════════

def prompt_int(prompt_text: str, default: int, min_val: int = 0, max_val: int = 99999) -> int:
    while True:
        raw = input(f"  {prompt_text} [{default}]: ").strip()
        if raw == "":
            return default
        try:
            val = int(raw)
            if min_val <= val <= max_val:
                return val
            warn(f"Please enter a number between {min_val} and {max_val}.")
        except ValueError:
            warn("Please enter a valid whole number.")

def prompt_choice(options: list[str], prompt_text: str = "Choose") -> str:
    for i, opt in enumerate(options, 1):
        print(f"    {cyan(str(i))}.  {opt}")
    while True:
        raw = input(f"\n  {prompt_text}: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        warn(f"Enter a number between 1 and {len(options)}.")

def prompt_graph() -> dict:
    """Let user pick one or all graphs."""
    section("Select Habit")
    opts = [f"{g['name']}  {dim('(' + g['unit'] + ')')}" for g in GRAPHS.values()]
    opts.append("All three habits")
    choice = prompt_choice(opts, "Which habit?")
    if "All three" in choice:
        return None   # caller handles None as "all"
    # match back to graph dict
    for g in GRAPHS.values():
        if g["name"] in choice:
            return g
    return None

def confirm(prompt_text: str) -> bool:
    raw = input(f"\n  {yellow(prompt_text)} [y/N]: ").strip().lower()
    return raw in ("y", "yes")


# ══════════════════════════════════════════════════════════════════
#  🚀  SETUP — run once to create account & graphs
# ══════════════════════════════════════════════════════════════════

def cmd_setup():
    header("🚀  FIRST-TIME SETUP")

    print(f"""
  {bold('Before continuing, make sure you have edited the script')}
  and set your {yellow('USERNAME')} and {yellow('TOKEN')} at the top of the file.

  USERNAME : {cyan(USERNAME)}
  TOKEN    : {cyan(TOKEN[:4] + '****' if len(TOKEN) > 4 else '****')}
""")

    if USERNAME == "your_username" or TOKEN == "your_secret_token":
        error("Please edit USERNAME and TOKEN in the script first, then re-run --setup.")
        sys.exit(1)

    if not confirm("Proceed with setup?"):
        print()
        return

    section("Creating Pixela account")
    res = api_create_user()
    if res.get("isSuccess"):
        success(f"Account '{USERNAME}' created!")
    else:
        msg = res.get("message", "")
        if "already exist" in msg.lower():
            warn(f"Account '{USERNAME}' already exists — skipping.")
        else:
            error(f"Could not create account: {msg}")
            sys.exit(1)

    section("Creating habit graphs")
    for g in GRAPHS.values():
        res = api_create_graph(g)
        if res.get("isSuccess"):
            success(f"{g['name']}  →  {dim(graph_url(g['id']))}")
        else:
            msg = res.get("message", "")
            if "already exist" in msg.lower():
                warn(f"Graph '{g['id']}' already exists — skipping.")
            else:
                error(f"Could not create graph '{g['id']}': {msg}")

    print(f"""
  {green('✨  Setup complete!')}

  View your graphs:
""")
    for g in GRAPHS.values():
        print(f"    {g['name']} → {cyan(graph_url(g['id']))}")

    print(f"""
  Run daily with:
    {bold('python pixela_tracker.py')}
""")


# ══════════════════════════════════════════════════════════════════
#  📝  LOG SESSION — morning or evening
#
#  FREE PLAN NOTE:
#  Because GET pixel is Supporter-only, the tracker cannot read your
#  existing value to accumulate on top of it. On the free plan:
#    • First log of the day  → creates the pixel (works perfectly)
#    • Second log of the day → overwrites with whatever you enter
#  Best practice on free plan: on your second session, enter the
#  FULL day total (morning + evening combined).
# ══════════════════════════════════════════════════════════════════

def cmd_log():
    header("📝  LOG A HABIT SESSION")

    now_hour = datetime.now().hour
    default_session = "Morning (5:30 AM)" if now_hour < 12 else "Evening"

    section("Session time")
    session = prompt_choice(["Morning (5:30 AM)", "Evening", "Other time"], "Which session?")

    section("Date")
    date_str = prompt_date("Date for this session", default="today")
    date_label = fmt_date(date_str)

    print(f"\n  {bold('Logging for:')} {cyan(date_label)}  {dim('(' + session + ')')}\n")

    divider()

    results = []

    # ── Push-ups ──────────────────────────────────────────────────
    section("💪  Push-ups")
    info(GRAPHS["1"]["note"])
    pushups = prompt_int("How many push-ups?", GRAPHS["1"]["default"], 1)
    ok, msg = upsert_pixel(GRAPHS["1"]["id"], date_str, pushups, mode="add")
    if ok:
        success(f"Push-ups logged  →  {msg} reps today")
        results.append(("Push-ups", True, msg))
    else:
        error(f"Failed: {msg}")
        results.append(("Push-ups", False, msg))

    # ── Reading ───────────────────────────────────────────────────
    section("📚  Book Reading")
    info(GRAPHS["2"]["note"])
    pages = prompt_int("How many pages did you read?", GRAPHS["2"]["default"], 1)
    ok, msg = upsert_pixel(GRAPHS["2"]["id"], date_str, pages, mode="add")
    if ok:
        success(f"Reading logged  →  {msg} pages today")
        results.append(("Reading", True, msg))
    else:
        error(f"Failed: {msg}")
        results.append(("Reading", False, msg))

    # ── Speaking ──────────────────────────────────────────────────
    section("🗣️   English Speaking")
    info(GRAPHS["3"]["note"])
    minutes = prompt_int("How many minutes did you practice?", GRAPHS["3"]["default"], 1)
    ok, msg = upsert_pixel(GRAPHS["3"]["id"], date_str, minutes, mode="add")
    if ok:
        success(f"Speaking logged  →  {msg} minutes today")
        results.append(("Speaking", True, msg))
    else:
        error(f"Failed: {msg}")
        results.append(("Speaking", False, msg))

    # ── Summary ───────────────────────────────────────────────────
    print()
    divider("═")
    print(f"  {bold('SESSION SUMMARY')}  —  {cyan(date_label)}")
    divider("═")
    all_ok = all(r[1] for r in results)
    for name, ok, msg in results:
        icon = green("✅") if ok else red("❌")
        print(f"  {icon}  {name:15s}  {dim(msg)}")

    if all_ok:
        print(f"\n  {green(bold('Great work! Keep it up! 🔥'))}\n")
    else:
        print(f"\n  {yellow('Some entries had issues — check errors above.')}\n")

    print(f"  {dim('View your graphs:')}")
    for g in GRAPHS.values():
        print(f"    {cyan(graph_url(g['id']))}")
    print()


# ══════════════════════════════════════════════════════════════════
#  ✏️  EDIT — set an exact value for any date
#
#  FREE PLAN NOTE:
#  The current stored value cannot be displayed (GET pixel is
#  Supporter-only). Just enter the new total you want to set.
# ══════════════════════════════════════════════════════════════════

def cmd_edit():
    header("✏️   EDIT / UPDATE A PIXEL")

    print(f"""
  Use this to:
    • Correct a value you logged incorrectly
    • Add data for a past date you forgot to log
    • Update yesterday's entry after a late session

  {yellow('This will OVERWRITE the existing value (not add to it).')}
""")

    # Pick graph
    section("Which habit?")
    opts = [f"{g['name']}  {dim('(' + g['unit'] + ')')}" for g in GRAPHS.values()]
    choice_label = prompt_choice(opts, "Habit to edit")
    graph = next(g for g in GRAPHS.values() if g["name"] in choice_label)

    # Pick date
    section("Which date?")
    date_str = prompt_date("Enter date", default="yesterday")

    # Try to show current value — may be unavailable on free plan
    section("Current value")
    existing = api_get_pixel(graph["id"], date_str)
    if is_supporter_error(existing):
        info("Current value not available on free plan — enter the new total directly.")
        current_val = None
    elif existing.get("isSuccess") is not False and "quantity" in existing:
        current_val = int(existing["quantity"])
        info(f"{graph['label']} on {fmt_date(date_str)}: {bold(str(current_val))} {graph['unit']}")
    else:
        info(f"No data yet for {graph['label']} on {fmt_date(date_str)}.")
        current_val = None

    # New value
    section("New value")
    default_val = current_val if current_val is not None else graph["default"]
    new_val = prompt_int(f"New {graph['unit']} count", default_val, 0)

    if current_val is not None and new_val == current_val:
        info("Value unchanged.")
        return

    if not confirm(f"Set {graph['label']} on {fmt_date(date_str)} to {bold(str(new_val))} {graph['unit']}?"):
        info("Edit cancelled.")
        return

    ok, msg = upsert_pixel(graph["id"], date_str, new_val, mode="set")
    if ok:
        success(f"Updated! {graph['label']} on {fmt_date(date_str)}: {bold(str(new_val))} {graph['unit']}")
    else:
        error(f"Update failed: {msg}")
    print()


# ══════════════════════════════════════════════════════════════════
#  🗑️  DELETE — remove a pixel on a specific date
# ══════════════════════════════════════════════════════════════════

def cmd_delete():
    header("🗑️   DELETE A PIXEL")

    warn("This permanently removes data for a specific date. Use with care.")

    section("Which habit?")
    opts = [f"{g['name']}  {dim('(' + g['unit'] + ')')}" for g in GRAPHS.values()]
    choice_label = prompt_choice(opts, "Habit")
    graph = next(g for g in GRAPHS.values() if g["name"] in choice_label)

    section("Which date?")
    date_str = prompt_date("Date to delete", default="today")

    # Try to show current value — may be unavailable on free plan
    existing = api_get_pixel(graph["id"], date_str)
    if is_supporter_error(existing):
        warn(f"You are about to delete: {graph['label']} on {fmt_date(date_str)} (value hidden on free plan)")
    elif existing.get("isSuccess") is not False and "quantity" in existing:
        val = existing["quantity"]
        warn(f"You are about to delete: {graph['label']} on {fmt_date(date_str)} = {bold(val)} {graph['unit']}")
    else:
        info(f"No pixel found for {graph['label']} on {fmt_date(date_str)}.")
        return

    if not confirm(f"Really delete this pixel? This CANNOT be undone."):
        info("Delete cancelled.")
        return

    res = api_delete_pixel(graph["id"], date_str)
    if res.get("isSuccess"):
        success(f"Pixel deleted: {graph['label']} on {fmt_date(date_str)}.")
    else:
        error(f"Delete failed: {res.get('message')}")
    print()


# ══════════════════════════════════════════════════════════════════
#  📊  VIEW — today's totals + graph URLs + stats
#
#  FREE PLAN NOTE:
#  Individual pixel reads and graph stats require Supporter.
#  Graph URLs always work and are shown regardless of plan.
# ══════════════════════════════════════════════════════════════════

def cmd_view():
    header("📊  STATS & GRAPHS")

    # ── Today ────────────────────────────────────────────────────
    section(f"Today's Totals  —  {cyan(fmt_date(today_str()))}")
    any_supporter_error = False
    for g in GRAPHS.values():
        res = api_get_pixel(g["id"], today_str())
        if is_supporter_error(res):
            any_supporter_error = True
            print(f"  {g['name']:25s} {dim('(requires Supporter plan)')}")
        elif res.get("isSuccess") is not False and "quantity" in res:
            qty = res["quantity"]
            bar = _mini_bar(int(qty), g["default"] * 2)
            print(f"  {g['name']:25s} {bold(qty):>6} {g['unit']:8s} {dim(bar)}")
        else:
            print(f"  {g['name']:25s} {dim('(no data yet)')}")

    if any_supporter_error:
        print(f"\n  {dim('Upgrade at: https://help.pixe.la/en/supporter-program')}")

    # ── All-time stats ───────────────────────────────────────────
    section("All-time Statistics (from Pixela)")
    for g in GRAPHS.values():
        stats = api_get_graph_stats(g["id"])
        if is_supporter_error(stats):
            print(f"\n  {bold(g['name'])}  {dim('— stats require Supporter plan')}")
            continue
        if stats.get("isSuccess") is not False:
            total   = stats.get("totalPixelsCount", "?")
            max_qty = stats.get("maxQuantity", "?")
            min_qty = stats.get("minQuantity", "?")
            print(f"\n  {bold(g['name'])}")
            print(f"    Days recorded : {cyan(str(total))}")
            print(f"    Highest day   : {green(str(max_qty))} {g['unit']}")
            print(f"    Lowest day    : {str(min_qty)} {g['unit']}")

    # ── Graph URLs ────────────────────────────────────────────────
    section("Graph URLs  (open in browser)")
    for g in GRAPHS.values():
        print(f"  {g['name']}")
        print(f"    {cyan(graph_url(g['id']))}")
        print(f"    {dim('SVG: ' + graph_svg_url(g['id']))}")
        print()


def _mini_bar(val: int, target: int, width: int = 20) -> str:
    """Simple ASCII progress bar."""
    if target <= 0:
        return ""
    filled = min(int((val / target) * width), width)
    return "[" + "█" * filled + "░" * (width - filled) + f"] {int(val/target*100)}%"


# ══════════════════════════════════════════════════════════════════
#  📅  HISTORY — view recent pixel data
#
#  FREE PLAN NOTE:
#  The pixel list endpoint (GET /pixels) is Supporter-only.
#  History will show a friendly message if unavailable.
# ══════════════════════════════════════════════════════════════════

def cmd_history():
    header("📅  RECENT HISTORY")

    section("How far back?")
    period = prompt_choice(["Last 7 days", "Last 14 days", "Last 30 days", "Last 90 days", "Custom range"], "Period")

    today  = datetime.now()
    if   "7"  in period: from_dt = today - timedelta(days=6)
    elif "14" in period: from_dt = today - timedelta(days=13)
    elif "30" in period: from_dt = today - timedelta(days=29)
    elif "90" in period: from_dt = today - timedelta(days=89)
    else:
        section("Custom date range")
        from_str = prompt_date("From date", default="-30")
        to_str   = prompt_date("To date",   default="today")
        from_dt  = datetime.strptime(from_str, "%Y%m%d")
        today    = datetime.strptime(to_str, "%Y%m%d")

    from_str = from_dt.strftime("%Y%m%d")
    to_str   = today.strftime("%Y%m%d")

    print(f"\n  {dim('Range: ' + fmt_date(from_str) + '  →  ' + fmt_date(to_str))}\n")

    supporter_noted = False
    for g in GRAPHS.values():
        section(g["name"])
        res = api_get_pixels(g["id"], from_str, to_str)

        if is_supporter_error(res):
            if not supporter_noted:
                warn("History requires the Pixela Supporter plan.")
                info("Upgrade at: https://help.pixe.la/en/supporter-program")
                supporter_noted = True
            else:
                warn("Requires Supporter plan.")
            continue

        if res.get("isSuccess") is False:
            warn(f"Could not fetch pixels: {res.get('message')}")
            continue

        pixels = res.get("pixels", [])
        if not pixels:
            info("No data in this range.")
            continue

        # Sort by date descending
        pixels.sort(key=lambda p: p["date"], reverse=True)
        total = sum(int(p["quantity"]) for p in pixels)
        avg   = total / len(pixels)

        print(f"  {'Date':<14} {'Value':>8}  {'Bar'}")
        divider("-", 52)
        for p in pixels:
            qty = int(p["quantity"])
            bar = _mini_bar(qty, g["default"] * 2, width=15)
            d   = fmt_date(p["date"])
            print(f"  {d:<28} {str(qty):>5} {g['unit']:<8} {dim(bar)}")

        divider("-", 52)
        print(f"  {'Total':28} {bold(str(total))} {g['unit']}")
        print(f"  {'Average/day':28} {round(avg, 1)} {g['unit']}")
        print()


# ══════════════════════════════════════════════════════════════════
#  🏠  MAIN INTERACTIVE MENU
# ══════════════════════════════════════════════════════════════════

MENU_OPTIONS = [
    ("📝  Log a session (morning / evening)",  cmd_log),
    ("📊  View today's stats & graphs",         cmd_view),
    ("✏️   Edit / update a past date",           cmd_edit),
    ("📅  View recent history",                  cmd_history),
    ("🗑️   Delete a pixel",                      cmd_delete),
    ("🚪  Exit",                                 None),
]

def main_menu():
    while True:
        banner()
        divider()
        for i, (label, _) in enumerate(MENU_OPTIONS, 1):
            print(f"    {cyan(str(i))}.  {label}")
        divider()

        raw = input(f"\n  {bold('Choose an option')}: ").strip()
        if not raw.isdigit() or not (1 <= int(raw) <= len(MENU_OPTIONS)):
            warn("Please enter a valid menu number.")
            continue

        label, fn = MENU_OPTIONS[int(raw) - 1]
        if fn is None:
            print(f"\n  {dim('Keep going — see you tomorrow! 💪')}\n")
            sys.exit(0)

        try:
            fn()
        except KeyboardInterrupt:
            print(f"\n\n  {dim('Cancelled.')}\n")
        except requests.exceptions.ConnectionError:
            error("No internet connection. Check your network and try again.")
        except Exception as e:
            error(f"Unexpected error: {e}")

        input(f"\n  {dim('Press Enter to return to menu...')}")


# ══════════════════════════════════════════════════════════════════
#  🎯  ENTRY POINT
# ══════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Pixela Habit Tracker — pushups, reading, english speaking",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--setup",   action="store_true", help="Create Pixela account and graphs (run once)")
    parser.add_argument("--log",     action="store_true", help="Log a session directly")
    parser.add_argument("--view",    action="store_true", help="View today's stats")
    parser.add_argument("--edit",    action="store_true", help="Edit a pixel on any date")
    parser.add_argument("--history", action="store_true", help="View recent pixel history")
    parser.add_argument("--delete",  action="store_true", help="Delete a pixel")
    args = parser.parse_args()

    try:
        if   args.setup:   cmd_setup()
        elif args.log:     cmd_log()
        elif args.view:    cmd_view()
        elif args.edit:    cmd_edit()
        elif args.history: cmd_history()
        elif args.delete:  cmd_delete()
        else:
            main_menu()

    except KeyboardInterrupt:
        print(f"\n\n  {dim('Goodbye!')}\n")
        sys.exit(0)
    except requests.exceptions.ConnectionError:
        error("No internet connection. Please check your network.")
        sys.exit(1)


if __name__ == "__main__":
    main()