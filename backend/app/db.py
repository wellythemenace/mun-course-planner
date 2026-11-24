"""SQLite storage. The catalog is rebuilt from data/ files on every start; ratings are kept."""
import csv
import hashlib
import json
import os
import re
import sqlite3
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from statistics import mean

BACKEND = Path(__file__).resolve().parent.parent
DATA = BACKEND / "data"
DB_PATH = Path(os.environ.get("PLANNER_DB", BACKEND / "planner.db"))
MIN_RATINGS = 3  # averages are hidden until this many students have rated
EXAM_TYPES = {"none", "take_home", "in_person", "mixed"}
READINGS = {"light", "medium", "heavy"}
MARKING = {"lenient", "fair", "harsh"}

SCHEMA = """
DROP TABLE IF EXISTS offerings;
DROP TABLE IF EXISTS instructors;
DROP TABLE IF EXISTS courses;
CREATE TABLE courses (
    code TEXT PRIMARY KEY, title TEXT NOT NULL, credit_hours INTEGER NOT NULL, kind TEXT NOT NULL,
    subject TEXT NOT NULL, level INTEGER NOT NULL, prereq_json TEXT NOT NULL, prereq_text TEXT,
    coreq_json TEXT NOT NULL, requires_acceptance TEXT, min_grades_json TEXT NOT NULL,
    required_for_major INTEGER NOT NULL, required_for_minor INTEGER NOT NULL, concentration TEXT,
    needs_review TEXT, note TEXT,
    alternatives_json TEXT NOT NULL DEFAULT '[]', concentrations_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE instructors (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, department TEXT);
CREATE TABLE offerings (
    id INTEGER PRIMARY KEY AUTOINCREMENT, course_code TEXT NOT NULL, term TEXT NOT NULL,
    instructor TEXT, department TEXT, source TEXT
);
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT NOT NULL, instructor TEXT, term TEXT,
    ease INTEGER NOT NULL CHECK (ease BETWEEN 1 AND 5),
    workload_hours REAL, assessments INTEGER, exam_type TEXT, readings TEXT, marking TEXT, comment TEXT,
    client_id TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'student', hidden INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (course_code, client_id)
);
"""


@contextmanager
def session():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _norm_course(c, kind):
    code = c["code"]
    m = re.match(r"^[A-Z]+ (\d)", code)
    return {
        "code": code, "title": c["title"], "credit_hours": c.get("credit_hours", 3), "kind": kind,
        "subject": code.split(" ")[0], "level": int(m.group(1)) * 1000 if m else 0,
        "prereq": c.get("prereq"), "prereq_text": c.get("prereq_text") or "none listed",
        "coreq": c.get("coreq") or [], "requires_program_acceptance": c.get("requires_program_acceptance"),
        "min_grades": c.get("min_grades") or {},
        "required_for_major": bool(c.get("required_for_major")),
        "required_for_minor": bool(c.get("required_for_minor")),
        "concentration": c.get("concentration"), "needs_review": c.get("needs_review"), "note": c.get("note"),
        "alternatives": c.get("alternatives") or [], "concentrations": c.get("concentrations") or {},
    }


def _read_csv(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        lines = [ln for ln in f if ln.strip() and not ln.lstrip().startswith("#")]
    return [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in csv.DictReader(lines)]


def _apply_load_overrides(catalog):
    """data/load_overrides.csv: hand-set hours per week for courses the flat defaults get wrong."""
    for r in _read_csv(DATA / "load_overrides.csv"):
        code = r.get("course_code", "").upper()
        try:
            hours = float(r.get("hours_per_week", ""))
        except ValueError:
            continue
        if code in catalog and 0 < hours <= 40:
            catalog[code]["hours_override"] = hours


def catalog_from_files():
    """-> (catalog, offering_rows, warnings). Shared by the API and the tests."""
    warnings = []
    with open(DATA / "courses_2026_27.json", encoding="utf-8") as f:
        cs = json.load(f)["courses"]
    with open(DATA / "electives_2026_27.json", encoding="utf-8") as f:
        el = json.load(f)["courses"]
    with open(DATA / "math_stats_2026_27.json", encoding="utf-8") as f:
        support = json.load(f)["courses"]
    catalog = {c["code"]: _norm_course(c, "cs") for c in cs}
    for c in el:
        catalog.setdefault(c["code"], _norm_course(c, "elective"))
    for c in support:
        catalog.setdefault(c["code"], _norm_course(c, "support"))
    rows = []
    for c in cs:
        for term, instructor in c["offered_2026_27"].items():
            rows.append((c["code"], term, instructor, "Computer Science", "department list (tentative)"))
    season_term = {"Fall": "Fall 2026", "Winter": "Winter 2027", "Spring": "Spring 2027"}
    for c in support:
        for season in c.get("usually_offered", []):
            rows.append((c["code"], season_term[season], None, "Mathematics and Statistics",
                         "department's usual pattern (not confirmed)"))
    for r in _read_csv(DATA / "offerings_extra.csv"):
        code = r.get("course_code", "").upper()
        if code not in catalog or not r.get("term") or not r.get("instructor"):
            warnings.append(f"offerings_extra.csv: skipped {r}")
            continue
        rows.append((code, r["term"], r["instructor"], r.get("department", ""), "added manually"))
    _apply_load_overrides(catalog)
    return catalog, rows, warnings


def offerings_map(rows):
    out = {}
    for code, term, instructor, _dept, _src in rows:
        out.setdefault(code, {})[term] = instructor
    return out


def init_db():
    catalog, rows, warnings = catalog_from_files()
    with session() as c:
        c.executescript(SCHEMA)
        for v in catalog.values():
            c.execute(
                "INSERT INTO courses VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (v["code"], v["title"], v["credit_hours"], v["kind"], v["subject"], v["level"],
                 json.dumps(v["prereq"]), v["prereq_text"], json.dumps(v["coreq"]),
                 v["requires_program_acceptance"], json.dumps(v["min_grades"]),
                 int(v["required_for_major"]), int(v["required_for_minor"]), v["concentration"],
                 v["needs_review"], v["note"], json.dumps(v["alternatives"]), json.dumps(v["concentrations"])))
        for code, term, instructor, dept, src in rows:
            if instructor:
                c.execute("INSERT OR IGNORE INTO instructors (name, department) VALUES (?, ?)", (instructor, dept))
            c.execute("INSERT INTO offerings (course_code, term, instructor, department, source) VALUES (?,?,?,?,?)",
                      (code, term, instructor, dept, src))
        for r in _read_csv(DATA / "seed_ratings.csv"):
            try:
                code = r["course_code"].upper()
                ease = int(r["ease"])
                assert code in catalog and 1 <= ease <= 5
                exam, reads, mark = r.get("exam_type") or None, r.get("readings") or None, r.get("marking") or None
                assert exam in EXAM_TYPES | {None} and reads in READINGS | {None} and mark in MARKING | {None}
                cid = "seed-" + hashlib.sha1(json.dumps(r, sort_keys=True).encode()).hexdigest()[:12]
                c.execute(
                    "INSERT OR IGNORE INTO ratings (course_code, instructor, term, ease, workload_hours, assessments,"
                    " exam_type, readings, marking, comment, client_id, source) VALUES (?,?,?,?,?,?,?,?,?,?,?, 'seed')",
                    (code, r.get("instructor") or None, r.get("term") or None, ease,
                     float(r["workload_hours"]) if r.get("workload_hours") else None,
                     int(r["assessments"]) if r.get("assessments") else None,
                     exam, reads, mark, (r.get("comment") or None), cid))
            except (KeyError, ValueError, AssertionError):
                warnings.append(f"seed_ratings.csv: skipped {r}")
    for w in warnings:
        print("WARNING:", w)
    return warnings


def load_catalog(conn):
    """Rebuild the catalog dict and offerings map from the database."""
    catalog = {}
    for r in conn.execute("SELECT * FROM courses"):
        catalog[r["code"]] = {
            "code": r["code"], "title": r["title"], "credit_hours": r["credit_hours"], "kind": r["kind"],
            "subject": r["subject"], "level": r["level"], "prereq": json.loads(r["prereq_json"]),
            "prereq_text": r["prereq_text"], "coreq": json.loads(r["coreq_json"]),
            "requires_program_acceptance": r["requires_acceptance"], "min_grades": json.loads(r["min_grades_json"]),
            "required_for_major": bool(r["required_for_major"]), "required_for_minor": bool(r["required_for_minor"]),
            "concentration": r["concentration"], "needs_review": r["needs_review"], "note": r["note"],
            "alternatives": json.loads(r["alternatives_json"]), "concentrations": json.loads(r["concentrations_json"]),
        }
    offerings = {}
    for r in conn.execute("SELECT course_code, term, instructor FROM offerings"):
        offerings.setdefault(r["course_code"], {})[r["term"]] = r["instructor"]
    _apply_load_overrides(catalog)
    return catalog, offerings


def rating_summary(conn, code=None, instructor=None):
    where, params = ["hidden = 0"], []
    if code:
        where.append("course_code = ?")
        params.append(code)
    if instructor:
        where.append("instructor = ?")
        params.append(instructor)
    rows = conn.execute(
        "SELECT ease, workload_hours, assessments, exam_type, readings, marking FROM ratings WHERE " + " AND ".join(where),
        params).fetchall()
    n = len(rows)
    out = {"count": n, "enough": n >= MIN_RATINGS, "min_needed": MIN_RATINGS}
    if n >= MIN_RATINGS:
        out["avg_ease"] = round(mean(r["ease"] for r in rows), 2)
        hours = [r["workload_hours"] for r in rows if r["workload_hours"] is not None]
        out["avg_workload_hours"] = round(mean(hours), 1) if hours else None
        out["exam_types"] = dict(Counter(r["exam_type"] for r in rows if r["exam_type"]))
        out["readings"] = dict(Counter(r["readings"] for r in rows if r["readings"]))
        out["marking"] = dict(Counter(r["marking"] for r in rows if r["marking"]))
    return out
