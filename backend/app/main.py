"""MUN Course Planner API: browse courses and electives, search professors, rate courses, build semester plans."""
import re
from typing import Literal, Optional

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from . import db
from .planner import build_plan, default_load, make_offered
from .prereq import is_satisfied, missing, normalize_code, outside_requirements

TERM_RE = re.compile(r"^(Fall|Winter|Spring) \d{4}$")

app = FastAPI(title="MUN Course Planner API")
db.init_db()


# ---------- request models ----------
class RatingIn(BaseModel):
    course_code: str
    ease: int = Field(ge=1, le=5)
    instructor: Optional[str] = Field(default=None, max_length=80)
    term: Optional[str] = Field(default=None, pattern=r"^(Fall|Winter|Spring) \d{4}$")
    workload_hours: Optional[float] = Field(default=None, ge=0, le=40)
    assessments: Optional[int] = Field(default=None, ge=0, le=30)
    exam_type: Optional[Literal["none", "take_home", "in_person", "mixed"]] = None
    readings: Optional[Literal["light", "medium", "heavy"]] = None
    marking: Optional[Literal["lenient", "fair", "harsh"]] = None
    comment: Optional[str] = Field(default=None, max_length=500)

    @field_validator("course_code")
    @classmethod
    def _norm(cls, v):
        return normalize_code(v)


class PlanRequest(BaseModel):
    completed: list[str] = []
    grades: dict[str, float] = {}
    terms: list[str] = Field(min_length=1, max_length=8)
    credit_target: int = Field(default=15, ge=3, le=21)
    strategy: Literal["lightest", "fastest", "balanced"] = "balanced"
    include_core: bool = True
    extra_courses: list[str] = []
    electives_per_term: int = Field(default=0, ge=0, le=3)
    cs_electives_per_term: int = Field(default=0, ge=0, le=3)
    elective_subjects: list[str] = []
    interest_areas: list[Literal["AI", "VCG", "DcC", "ToC"]] = []
    accepted_into_major: bool = True

    @field_validator("elective_subjects")
    @classmethod
    def _subjects(cls, v):
        return [x.strip().upper() for x in v]

    @field_validator("completed", "extra_courses")
    @classmethod
    def _norm_list(cls, v):
        return [normalize_code(x) for x in v]

    @field_validator("grades")
    @classmethod
    def _norm_grades(cls, v):
        return {normalize_code(k): g for k, g in v.items()}

    @field_validator("terms")
    @classmethod
    def _terms(cls, v):
        for t in v:
            if not TERM_RE.match(t):
                raise ValueError(f"Bad term {t!r}. Use e.g. 'Fall 2026'.")
        return v


class EligibilityRequest(BaseModel):
    completed: list[str] = []

    @field_validator("completed")
    @classmethod
    def _norm_list(cls, v):
        return [normalize_code(x) for x in v]


# ---------- helpers ----------
def _summary(row, terms, conn):
    return {
        "code": row["code"], "title": row["title"], "credit_hours": row["credit_hours"], "kind": row["kind"],
        "subject": row["subject"], "level": row["level"], "prereq_text": row["prereq_text"],
        "offered_terms": sorted(terms), "needs_review": row["needs_review"],
        "required_for_major": bool(row["required_for_major"]),
        "rating": db.rating_summary(conn, code=row["code"]),
    }


def _offered_terms(conn):
    out = {}
    for r in conn.execute("SELECT course_code, term FROM offerings"):
        out.setdefault(r["course_code"], set()).add(r["term"])
    return out


def _professor_rows(conn, where="", params=()):
    sql = ("SELECT i.id, i.name, i.department, o.term, o.course_code, c.title FROM instructors i "
           "LEFT JOIN offerings o ON o.instructor = i.name LEFT JOIN courses c ON c.code = o.course_code "
           + where + " ORDER BY i.name, o.term, o.course_code")
    people = {}
    for r in conn.execute(sql, params):
        p = people.setdefault(r["id"], {"id": r["id"], "name": r["name"], "department": r["department"], "offerings": []})
        if r["course_code"]:
            p["offerings"].append({"term": r["term"], "course_code": r["course_code"], "title": r["title"]})
    for p in people.values():
        p["rating"] = db.rating_summary(conn, instructor=p["name"])
    return list(people.values())


# ---------- routes ----------
@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/outside-courses")
def outside_courses():
    """Non-catalog courses (MATH, STAT, BIOL...) that CS courses name as prerequisites, and who needs them."""
    with db.session() as conn:
        catalog, _ = db.load_catalog(conn)
        return [{"code": k, "needed_by": v} for k, v in outside_requirements(catalog).items()]


@app.get("/api/courses")
def list_courses(q: str = "", kind: Optional[Literal["cs", "elective", "support"]] = None, term: Optional[str] = None,
                 subject: Optional[str] = None, no_prereq: bool = False, limit: int = Query(100, le=300)):
    with db.session() as conn:
        offered = _offered_terms(conn)
        out = []
        for r in conn.execute("SELECT * FROM courses ORDER BY code"):
            terms = offered.get(r["code"], set())
            if kind and r["kind"] != kind:
                continue
            if subject and r["subject"] != subject.upper():
                continue
            if no_prereq and r["prereq_json"] != "null":
                continue
            if term and term not in terms:
                continue
            if q and q.lower() not in (r["code"] + " " + r["title"]).lower():
                continue
            out.append(_summary(r, terms, conn))
        return out[:limit]


@app.get("/api/courses/{code}")
def course_detail(code: str):
    code = normalize_code(code)
    with db.session() as conn:
        row = conn.execute("SELECT * FROM courses WHERE code = ?", (code,)).fetchone()
        if row is None:
            raise HTTPException(404, "Course not found")
        catalog, offerings = db.load_catalog(conn)
        detail = _summary(row, set(offerings.get(code, {})), conn)
        detail.update({
            "prereq": catalog[code]["prereq"], "coreq": catalog[code]["coreq"],
            "requires_program_acceptance": row["requires_acceptance"], "note": row["note"],
            "required_for_major": bool(row["required_for_major"]), "concentration": row["concentration"],
            "offerings": [dict(r) for r in conn.execute(
                "SELECT term, instructor, department FROM offerings WHERE course_code = ? ORDER BY term", (code,))],
            "recent_comments": [dict(r) for r in conn.execute(
                "SELECT ease, term, instructor, comment, source, created_at FROM ratings "
                "WHERE course_code = ? AND hidden = 0 AND comment IS NOT NULL ORDER BY id DESC LIMIT 10", (code,))],
        })
        return detail


@app.post("/api/courses/{code}/eligibility")
def eligibility(code: str, body: EligibilityRequest):
    code = normalize_code(code)
    with db.session() as conn:
        catalog, _ = db.load_catalog(conn)
        if code not in catalog:
            raise HTTPException(404, "Course not found")
        done = set(body.completed)
        needs = missing(catalog[code]["prereq"], done, catalog)
        return {"code": code, "eligible": not needs, "missing": needs,
                "requires_program_acceptance": catalog[code]["requires_program_acceptance"],
                "prereq_text": catalog[code]["prereq_text"]}


@app.get("/api/electives")
def electives(q: str = "", term: Optional[str] = None, sort: Literal["ease", "alpha"] = "ease"):
    with db.session() as conn:
        offered = _offered_terms(conn)
        out = []
        for r in conn.execute("SELECT * FROM courses WHERE kind = 'elective' ORDER BY code"):
            terms = offered.get(r["code"], set())
            if term and terms and term not in terms:
                continue
            if q and q.lower() not in (r["code"] + " " + r["title"]).lower():
                continue
            out.append(_summary(r, terms, conn))
        if sort == "ease":
            out.sort(key=lambda c: (not c["rating"]["enough"], -(c["rating"].get("avg_ease") or 0), c["code"]))
        return out


@app.get("/api/professors")
def search_professors(q: str = "", term: Optional[str] = None):
    where, params = [], []
    if q:
        where.append("LOWER(i.name) LIKE ?")
        params.append(f"%{q.lower()}%")
    if term:
        where.append("o.term = ?")
        params.append(term)
    with db.session() as conn:
        return _professor_rows(conn, ("WHERE " + " AND ".join(where)) if where else "", params)


@app.get("/api/professors/{professor_id}")
def professor(professor_id: int):
    with db.session() as conn:
        found = _professor_rows(conn, "WHERE i.id = ?", (professor_id,))
        if not found:
            raise HTTPException(404, "Professor not found")
        return found[0]


@app.post("/api/ratings", status_code=201)
def submit_rating(body: RatingIn, x_client_id: Optional[str] = Header(default=None)):
    if not x_client_id or not (8 <= len(x_client_id) <= 64):
        raise HTTPException(400, "Send an X-Client-Id header (8 to 64 characters) so one person can rate a course once.")
    with db.session() as conn:
        if conn.execute("SELECT 1 FROM courses WHERE code = ?", (body.course_code,)).fetchone() is None:
            raise HTTPException(404, "Course not found")
        conn.execute(
            "INSERT INTO ratings (course_code, instructor, term, ease, workload_hours, assessments, exam_type,"
            " readings, marking, comment, client_id) VALUES (?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(course_code, client_id) DO UPDATE SET instructor=excluded.instructor, term=excluded.term,"
            " ease=excluded.ease, workload_hours=excluded.workload_hours, assessments=excluded.assessments,"
            " exam_type=excluded.exam_type, readings=excluded.readings, marking=excluded.marking,"
            " comment=excluded.comment, created_at=CURRENT_TIMESTAMP",
            (body.course_code, body.instructor, body.term, body.ease, body.workload_hours, body.assessments,
             body.exam_type, body.readings, body.marking, (body.comment or "").strip() or None, x_client_id))
        return {"saved": True, "rating": db.rating_summary(conn, code=body.course_code)}


@app.post("/api/plan")
def make_plan(body: PlanRequest):
    with db.session() as conn:
        catalog, offerings = db.load_catalog(conn)
        cache = {}

        def summary(code):
            if code not in cache:
                cache[code] = db.rating_summary(conn, code=code)
            return cache[code]

        def load(code):
            s = summary(code)
            if s["enough"] and s.get("avg_workload_hours") is not None:
                return s["avg_workload_hours"], "ratings"
            src = "override" if catalog[code].get("hours_override") is not None else "default"
            return default_load(catalog[code]), src

        def ease(code):
            s = summary(code)
            return s.get("avg_ease") if s["enough"] else None

        return build_plan(
            catalog=catalog, completed=body.completed, terms=body.terms, credit_target=body.credit_target,
            strategy=body.strategy, include_core=body.include_core, extra_courses=body.extra_courses,
            electives_per_term=body.electives_per_term, cs_electives_per_term=body.cs_electives_per_term,
            elective_subjects=body.elective_subjects, interest_areas=body.interest_areas,
            accepted_into_major=body.accepted_into_major,
            grades=body.grades, offered=make_offered(catalog, offerings), load=load, ease=ease,
            instructor_for=lambda code, term: offerings.get(code, {}).get(term))
