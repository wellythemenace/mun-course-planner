"""Semester plan generator. Pure Python: no web or database imports, so it is easy to test.

Idea: each term, take the courses whose prerequisites are already done and that are
offered that term, rank them by the chosen strategy, and fill up to the credit target.
"""
from collections import Counter

from .prereq import is_satisfied, leaf_codes, missing

# Terms the department has published (Spring 2027 is "to be determined", so nothing is scheduled in it).
KNOWN_TERMS = {"Fall 2026", "Winter 2027", "Spring 2027"}
SEASON_ORDER = {"Winter": 0, "Spring": 1, "Fall": 2}
HEAVY_HOURS = 9.0
EARLY_TERMS = 2          # "first semesters": the first two terms of the plan...
EARLY_CREDIT_HOURS = 30  # ...while the student has fewer than this many credit hours done
MATH_SUBJECTS = {"MATH", "STAT"}  # at most one MATH and one STAT per term, unless only math and stats are left
MAX_HEAVY_PER_TERM = 2


def math_fits(picked_so_far, new_math, left_to_take):
    """At most one MATH and one STAT course per term, unless math and stats are all that is left to take."""
    have = Counter(c.split()[0] for c in picked_so_far if c.split()[0] in MATH_SUBJECTS)
    add = Counter(c.split()[0] for c in new_math)
    if all(have[subject] + n <= 1 for subject, n in add.items()):
        return True
    return all(c.split()[0] in MATH_SUBJECTS for c in left_to_take)


def term_key(term: str):
    season, year = term.split()
    return int(year), SEASON_ORDER[season]


def make_offered(catalog, offerings, known_terms=KNOWN_TERMS):
    """offerings: {course_code: {term: instructor}}.
    Returns offered(code, term) -> {"offered", "assumed", "unknown"}."""
    last_known = max(term_key(t) for t in known_terms)

    def offered(code, term):
        course = catalog[code]
        by_term = offerings.get(code, {})
        if course["kind"] == "elective":
            # electives have no authoritative schedule loaded, so a listed term is a bonus, not a limit
            if term in by_term:
                return {"offered": True, "assumed": False, "unknown": False}
            return {"offered": True, "assumed": True, "unknown": True}
        if course["kind"] == "support" and not by_term:
            return {"offered": True, "assumed": True, "unknown": True}
        if term in known_terms:
            return {"offered": term in by_term, "assumed": False, "unknown": False}
        if term_key(term) > last_known:
            season = term.split()[0]
            if any(t.startswith(season) for t in by_term):
                return {"offered": True, "assumed": True, "unknown": False}
        return {"offered": False, "assumed": False, "unknown": False}

    return offered


def default_load(course) -> float:
    """Rough hours per week when nobody has rated the course yet.
    A hand-set value in data/load_overrides.csv wins over the flat guess below."""
    if course.get("hours_override") is not None:
        return float(course["hours_override"])
    if course["credit_hours"] <= 1:
        return 2.0
    if course["kind"] == "elective":
        return 5.0
    if course["kind"] == "support":
        return 7.0
    return {1000: 6.0, 2000: 8.0, 3000: 9.0, 4000: 10.0}.get(course["level"], 8.0)


def _pick_required(req, done, wanted, catalog):
    """Which schedulable CS courses does this requirement still need?"""
    if req is None:
        return []
    if isinstance(req, str):
        return [req]
    if "all" in req:
        return [x for r in req["all"] for x in _pick_required(r, done, wanted, catalog)]
    if "any" in req:
        for r in req["any"]:
            if is_satisfied(r, done | wanted, catalog):
                return []
        for r in req["any"]:
            opts = _pick_required(r, done, wanted, catalog)
            if opts and all(o in catalog and catalog[o]["kind"] in ("cs", "support") for o in opts):
                return opts
        return []
    return []


def _expand_prereqs(wanted, done, catalog):
    out = set(wanted)
    stack = list(wanted)
    while stack:
        code = stack.pop()
        for need in _pick_required(catalog[code]["prereq"], done, out, catalog):
            if need in catalog and need not in out and need not in done and catalog[need]["kind"] in ("cs", "support"):
                out.add(need)
                stack.append(need)
    return out


def build_plan(*, catalog, completed, terms, credit_target=15, strategy="balanced",
               include_core=True, extra_courses=(), electives_per_term=0,
               cs_electives_per_term=0, elective_subjects=(), interest_areas=(),
               accepted_into_major=True, grades=None,
               offered, load, ease, instructor_for):
    """load(code) -> (hours_per_week, source); ease(code) -> average ease or None;
    instructor_for(code, term) -> name or None."""
    grades = grades or {}
    done = set(completed)
    # Admission to the CS major needs MATH 1000 (or 1006) and COMP 1001 and 1002 (calendar 11.4.1), and COMP 2001 and up
    # need that admission. So a student past COMP 1001 and 1002 who is in the major has normally done MATH 1000 already.
    assumed_math_1000 = (accepted_into_major and {"COMP 1001", "COMP 1002"} <= done and "MATH 1000" in catalog
                         and "MATH 1000" not in done and not any(a in done for a in catalog["MATH 1000"]["alternatives"]))
    if assumed_math_1000:
        done.add("MATH 1000")
    unknown_codes = [c for c in extra_courses if c not in catalog]

    def alt_done(code, have):
        return any(a in have for a in catalog[code]["alternatives"])

    wanted = set()
    if include_core:
        wanted |= {c for c, v in catalog.items()
                   if v["required_for_major"] and c not in done and not alt_done(c, done)}
    wanted |= {c for c in extra_courses if c in catalog}
    wanted = _expand_prereqs(wanted, done, catalog) - done

    closure = {}

    def closure_of(code):
        if code in closure:
            return closure[code]
        closure[code] = set()  # guards against cycles
        out = set()
        course = catalog.get(code)
        if course:
            for leaf in leaf_codes(course["prereq"]):
                out.add(leaf)
                out |= closure_of(leaf)
        closure[code] = out
        return out

    # how many CS courses depend on each course (used to rank CS electives for "fastest")
    dependents_total = Counter()
    for code in catalog:
        if catalog[code]["kind"] == "cs":
            for leaf in closure_of(code):
                dependents_total[leaf] += 1

    planned = set()
    plan_terms = []
    math_capped = set()
    stat_deferred = set()
    early_student = sum(catalog[c]["credit_hours"] for c in done if c in catalog) < EARLY_CREDIT_HOURS
    any_assumed = any_unknown = any_cs_elective = False
    roles = {}
    subject_use = Counter()

    def blockers(code, term, available):
        course = catalog[code]
        reasons = []
        if not offered(code, term)["offered"]:
            reasons.append("not offered")
        if not is_satisfied(course["prereq"], available, catalog):
            reasons.append("prerequisites")
        if course.get("requires_program_acceptance") and not accepted_into_major:
            reasons.append("needs program acceptance")
        return reasons

    def bundle_of(code):
        members, stack = set(), [code]
        while stack:
            c = stack.pop()
            if c in members or c in done or c in planned or c not in catalog:
                continue
            members.add(c)
            stack.extend(catalog[c]["coreq"])
        return members

    for term_idx, term in enumerate(terms):
        available = done | planned
        keep_stat_out = early_student and term_idx < EARLY_TERMS
        deferred_stat = []
        remaining = wanted - planned
        picked, ch_total, heavy_total = [], 0, 0

        def downstream(code):
            return sum(1 for w in remaining if code in closure_of(w))

        # 1. electives first, so they reserve credit hours.
        # Rated electives rank by ease. Unrated ones prefer first-year courses and a variety of subjects.
        if electives_per_term:
            pool = [c for c, v in catalog.items()
                    if v["kind"] == "elective" and c not in done and c not in planned and c not in wanted
                    and (not elective_subjects or v["subject"] in elective_subjects)]
            for _ in range(electives_per_term):
                best = None
                for c in pool:
                    if c in picked or blockers(c, term, available):
                        continue
                    if ch_total + catalog[c]["credit_hours"] > credit_target:
                        continue
                    e = ease(c)
                    k = (-(e if e is not None else 3.0), subject_use[catalog[c]["subject"]],
                         catalog[c]["level"], load(c)[0], c)
                    if best is None or k < best[0]:
                        best = (k, c)
                if best is None:
                    break
                c = best[1]
                picked.append(c)
                roles[c] = "elective"
                subject_use[catalog[c]["subject"]] += 1
                ch_total += catalog[c]["credit_hours"]

        # 2. required / wanted courses, grouped with their co-requisites
        bundles, seen = [], set()
        for code in sorted(remaining):
            b = frozenset(bundle_of(code))
            if not b or b in seen:
                continue
            seen.add(b)
            if all(not blockers(m, term, available) for m in b):
                bundles.append(b)

        def stats(b):
            ch = sum(catalog[m]["credit_hours"] for m in b)
            hours = sum(load(m)[0] for m in b)
            down = max(downstream(m) for m in b)
            heavy = sum(1 for m in b if load(m)[0] >= HEAVY_HOURS)
            return ch, hours, down, heavy

        def key(b):
            _, hours, down, _ = stats(b)
            tie = sorted(b)[0]
            if strategy == "fastest":
                return (-down, hours, tie)
            if strategy == "lightest":
                return (hours, -down, tie)
            return (hours - 2.0 * down, tie)

        for b in sorted(bundles, key=key):
            new = b - set(picked)  # bundles can overlap (e.g. COMP 2004 alone and with its co-requisites)
            if not new:
                continue
            ch, _, _, heavy = stats(new)
            if ch_total + ch > credit_target:
                continue
            # No statistics in the first semesters if it can be avoided (see the fallback after step 2b).
            if keep_stat_out and any(m.split()[0] == "STAT" for m in new):
                deferred_stat.append(b)
                stat_deferred.update(m for m in new if m.split()[0] == "STAT")
                continue
            # One math course per term, unless every course still left to take is a math course.
            new_math = [m for m in new if catalog[m]["subject"] in MATH_SUBJECTS]
            if new_math and not math_fits(picked, new_math, wanted - planned):
                math_capped.update(new_math)
                continue
            if strategy != "fastest" and heavy_total + heavy > MAX_HEAVY_PER_TERM:
                continue
            for m in sorted(new):
                roles[m] = ("core" if catalog[m]["required_for_major"]
                            else "prereq" if catalog[m]["kind"] == "support" else "chosen")
            picked.extend(sorted(new))
            ch_total += ch
            heavy_total += heavy

        # 2b. CS electives: eligible upper-level CS courses beyond the core, to fill the term
        if cs_electives_per_term:
            cands = [c for c, v in catalog.items()
                     if v["kind"] == "cs" and v["level"] >= 3000
                     and c not in done and c not in planned and c not in wanted and c not in picked]

            def fit_tier(c):
                tiers = [catalog[c]["concentrations"].get(a) for a in interest_areas]
                return 0 if "required" in tiers else 1 if "elective" in tiers else 2

            def cs_key(c):
                match = fit_tier(c)
                h, deps, lvl = load(c)[0], dependents_total.get(c, 0), catalog[c]["level"]
                if strategy == "fastest":
                    return (match, -deps, h, lvl, c)
                if strategy == "lightest":
                    return (match, h, lvl, c)
                return (match, h - 1.5 * deps, lvl, c)

            count = 0
            for c in sorted(cands, key=cs_key):
                if count >= cs_electives_per_term:
                    break
                if blockers(c, term, available):
                    continue
                ch = catalog[c]["credit_hours"]
                if ch_total + ch > credit_target:
                    continue
                hv = 1 if load(c)[0] >= HEAVY_HOURS else 0
                if strategy != "fastest" and heavy_total + hv > MAX_HEAVY_PER_TERM:
                    continue
                picked.append(c)
                roles[c] = "cs_elective"
                any_cs_elective = True
                ch_total += ch
                heavy_total += hv
                count += 1

        # Fallback: if the term would be empty without it, a statistics course is better than nothing.
        if keep_stat_out and not picked:
            for b in deferred_stat:
                new = b - set(picked)
                ch, _, _, _ = stats(new)
                if new and ch_total + ch <= credit_target:
                    for m in sorted(new):
                        roles[m] = "core" if catalog[m]["required_for_major"] else "prereq"
                    picked.extend(sorted(new))
                    ch_total += ch

        # 3. describe the term
        lines, hours_total = [], 0.0
        for c in picked:
            course = catalog[c]
            h, src = load(c)
            off = offered(c, term)
            any_assumed |= off["assumed"] and not off["unknown"]
            any_unknown |= off["unknown"]
            warns = []
            for code, minimum in course.get("min_grades", {}).items():
                g = grades.get(code)
                if code in done and g is not None and g < minimum:
                    warns.append(f"Usually needs at least {minimum}% in {code}. You entered {g}%.")
            hours_total += h
            lines.append({
                "code": c, "title": course["title"], "credit_hours": course["credit_hours"],
                "kind": course["kind"], "role": roles.get(c, "chosen"),
                "load_hours": h, "load_source": src, "ease": ease(c),
                "offering_assumed": off["assumed"] and not off["unknown"],
                "offering_unknown": off["unknown"],
                "instructor": instructor_for(c, term), "warnings": warns,
            })
        term_warnings = []
        if hours_total > 45:
            term_warnings.append(f"Very heavy: about {round(hours_total)} hours of work per week.")
        if ch_total < credit_target - 2 and ((wanted - planned - set(picked)) or electives_per_term or cs_electives_per_term):
            term_warnings.append("Under the credit target. Nothing else is eligible this term. Check the MATH/STAT "
                                 "courses in your completed list, and whether more courses are offered.")
        plan_terms.append({"term": term, "courses": lines, "credit_hours": ch_total,
                           "est_hours_per_week": round(hours_total, 1), "warnings": term_warnings})
        planned |= set(picked)

    unplaced = []
    for code in sorted(wanted - planned):
        reasons = []
        unmet = missing(catalog[code]["prereq"], done | planned, catalog)
        if unmet:
            reasons.append("still needs: " + "; ".join(unmet))
        if not any(offered(code, t)["offered"] for t in terms):
            reasons.append("not offered in the terms you chose")
        if code in stat_deferred:
            reasons.append("statistics is kept out of your first two terms. Try more terms.")
        if code in math_capped:
            reasons.append("only one MATH course and one STAT course are planned per term while other required courses remain. Try more terms.")
        if not reasons:
            reasons.append("no room within the credit target. Try more terms or a higher target.")
        unplaced.append({"code": code, "title": catalog[code]["title"], "reasons": reasons})

    # Why are the courses in the student's interest areas not in the plan?
    interest_blocked = []
    if interest_areas:
        for code in sorted(catalog):
            c = catalog[code]
            wanted_here = [a for a in interest_areas if c["concentrations"].get(a) == "required"]
            if c["kind"] != "cs" or not wanted_here or code in done or code in planned:
                continue
            reasons = []
            unmet = missing(c["prereq"], done | planned, catalog)
            if unmet:
                reasons.append("still needs: " + "; ".join(unmet))
            if not any(offered(code, t)["offered"] for t in terms):
                reasons.append("not offered in the terms you chose")
            if not reasons:
                reasons.append("eligible, but no room this plan. Raise 'Other CS courses per term' or the credit target.")
            interest_blocked.append({"code": code, "title": c["title"], "area": wanted_here[0], "reasons": reasons})

    # Progress toward the Major in Computer Science (calendar 11.4.4)
    have = done | planned
    cs_have = [c for c in have if c in catalog and catalog[c]["kind"] == "cs"]
    hours = lambda min_level: sum(catalog[c]["credit_hours"] for c in cs_have if catalog[c]["level"] >= min_level)
    degree_progress = {
        "cs_hours": {"have": hours(0), "need": 45},
        "upper_hours": {"have": hours(3000), "need": 18},
        "fourk_hours": {"have": hours(4000), "need": 6},
        "required_missing": sorted(c for c, v in catalog.items()
                                   if v["required_for_major"] and c not in have and not alt_done(c, have)),
        "note": "Counts completed and planned courses that are in the catalog. Based on the Major in Computer Science "
                "(45 CS credit hours: the core, 12 more at 3000+, and 6 at 4000+, plus the required math and statistics).",
    }

    assumptions = [
        *(["MATH 1000 is assumed done. Admission to the CS major requires it (or MATH 1006), so a student past COMP 1001 and 1002 "
           "has normally taken it. Untick 'accepted into the major' to plan it."] if assumed_math_1000 else []),
        "Statistics courses are kept out of your first two terms while you have under 30 credit hours done, if possible.",
        "At most one MATH course and one STAT course per term, unless math and stats are all that is left to take.",
        "You are accepted into the CS major" if accepted_into_major else "You are NOT accepted into the CS major yet, so those courses were skipped",
        "MATH, STAT and other non-COMP prerequisites count only if they are in your completed list",
        "Hours per week use default estimates unless a course has 3 or more student ratings",
    ]
    if any_assumed:
        assumptions.append("Terms after Winter 2027 reuse the 2026-27 pattern. The department has not published them.")
    if any_cs_elective:
        assumptions.append("CS electives are picked from eligible 3000/4000-level courses. How many the degree "
                           "requires is not loaded, so check your degree requirements.")
    if any_unknown:
        assumptions.append("Electives and math/statistics courses with no offering data are assumed available. "
                           "Confirm them in the registrar's schedule.")
    return {"terms": plan_terms, "unplaced": unplaced, "interest_blocked": interest_blocked,
            "degree_progress": degree_progress, "unknown_codes": unknown_codes, "assumptions": assumptions}
