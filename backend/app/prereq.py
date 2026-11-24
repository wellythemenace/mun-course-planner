"""Evaluate prerequisite requirements from the course data.

A requirement is one of:
  None                          nothing required
  "COMP 2001"                   that course must be completed
  {"all": [req, ...]}           every item
  {"any": [req, ...]}           at least one item
  {"credits_from": {"subject": "COMP", "min_level": 3000, "hours": 6}}
"""
import re


def normalize_code(code: str) -> str:
    return re.sub(r"\s+", " ", code.strip().upper())


def code_parts(code: str):
    """'COMP 3200' -> ('COMP', 3000)."""
    m = re.match(r"^([A-Z]+) (\d)", code)
    if not m:
        return code, 0
    return m.group(1), int(m.group(2)) * 1000


def course_info(code: str, catalog: dict):
    subject, level = code_parts(code)
    course = catalog.get(code)
    return subject, level, (course["credit_hours"] if course else 3)


def is_satisfied(req, completed, catalog) -> bool:
    if req is None:
        return True
    if isinstance(req, str):
        return req in completed
    if "all" in req:
        return all(is_satisfied(r, completed, catalog) for r in req["all"])
    if "any" in req:
        return any(is_satisfied(r, completed, catalog) for r in req["any"])
    if "credits_from" in req:
        spec = req["credits_from"]
        subjects = [s.strip() for s in spec["subject"].split(" or ")]
        total = 0
        for code in completed:
            subject, level, hours = course_info(code, catalog)
            if subject in subjects and level >= spec["min_level"]:
                total += hours
        return total >= spec["hours"]
    raise ValueError(f"Unknown requirement: {req!r}")


def describe(req) -> str:
    if req is None:
        return "nothing"
    if isinstance(req, str):
        return req
    if "all" in req:
        return "(" + " + ".join(describe(r) for r in req["all"]) + ")"
    if "any" in req:
        return " or ".join(describe(r) for r in req["any"])
    spec = req["credits_from"]
    return f"{spec['hours']} credit hours of {spec['subject']} at {spec['min_level']}+"


def missing(req, completed, catalog) -> list:
    """Plain-language list of what is still needed (empty if satisfied)."""
    if is_satisfied(req, completed, catalog):
        return []
    if isinstance(req, str):
        return [req]
    if "all" in req:
        out = []
        for r in req["all"]:
            out += missing(r, completed, catalog)
        return out
    if "any" in req:
        return ["one of: " + describe(req)]
    return [describe(req)]


def leaf_codes(req):
    """Every course code that appears anywhere in a requirement."""
    if req is None:
        return
    if isinstance(req, str):
        yield req
    elif "all" in req:
        for r in req["all"]:
            yield from leaf_codes(r)
    elif "any" in req:
        for r in req["any"]:
            yield from leaf_codes(r)


def outside_requirements(catalog) -> dict:
    """Courses that CS prerequisites name but the catalog does not hold (MATH, STAT, BIOL...).
    -> {code: [catalog courses that name it]}"""
    out = {}
    for code, course in catalog.items():
        for leaf in leaf_codes(course["prereq"]):
            if leaf not in catalog:
                out.setdefault(leaf, set()).add(code)
    return {k: sorted(v) for k, v in sorted(out.items())}
