import unittest

from app import db
from app.planner import build_plan, default_load, make_offered

CATALOG, ROWS, _WARN = db.catalog_from_files()
OFFERINGS = db.offerings_map(ROWS)
OFFERED = make_offered(CATALOG, OFFERINGS)


def plan(ease_by_code=None, **kw):
    ease_by_code = ease_by_code or {}
    args = dict(
        catalog=CATALOG, completed=[], terms=["Fall 2026", "Winter 2027"],
        offered=OFFERED,
        load=lambda c: (default_load(CATALOG[c]), "default"),
        ease=lambda c: ease_by_code.get(c),
        instructor_for=lambda c, t: OFFERINGS.get(c, {}).get(t))
    args.update(kw)
    return build_plan(**args)


def codes(term_entry):
    return {c["code"] for c in term_entry["courses"]}


def maths(term_entry, subject):
    return [c for c in codes(term_entry) if c.startswith(subject + " ")]


def comp(term_entry):
    return {c for c in codes(term_entry) if c.startswith("COMP")}


FIRST_YEAR = ["COMP 1001", "COMP 1002", "COMP 1003"]


class PlannerTests(unittest.TestCase):
    def test_prereqs_are_not_taken_in_the_same_term(self):
        p = plan(completed=FIRST_YEAR)
        fall, winter = p["terms"]
        self.assertEqual(comp(fall), {"COMP 2001", "COMP 2002", "COMP 2003"})
        self.assertEqual(comp(winter), {"COMP 2004", "COMP 2005", "COMP 2006", "COMP 2007", "COMP 2008"})

    def test_corequisites_travel_together(self):
        for strategy in ("lightest", "fastest", "balanced"):
            p = plan(completed=FIRST_YEAR, strategy=strategy,
                     terms=["Fall 2026", "Winter 2027", "Fall 2027", "Winter 2028"])
            seen = set(FIRST_YEAR)
            for t in p["terms"]:
                seen |= codes(t)
                if "COMP 2006" in codes(t):
                    self.assertTrue({"COMP 2004", "COMP 2007", "COMP 2008"} <= seen, strategy)
            self.assertEqual(p["unplaced"], [], strategy)

    def test_math_that_cannot_finish_in_time_is_reported(self):
        p = plan(completed=FIRST_YEAR + ["COMP 2001", "COMP 2002"], include_core=False, extra_courses=["COMP 3301"])
        unplaced = {u["code"]: u["reasons"] for u in p["unplaced"]}
        self.assertIn("COMP 3301", unplaced)
        self.assertIn("MATH 2000", " ".join(unplaced["COMP 3301"]))

    def test_math_in_completed_list_unlocks_it(self):
        p = plan(completed=FIRST_YEAR + ["COMP 2001", "COMP 2002", "MATH 2000", "MATH 2050"],
                 include_core=False, extra_courses=["COMP 3301"], terms=["Fall 2026"])
        self.assertEqual(codes(p["terms"][0]), {"COMP 3301"})

    def test_extra_course_pulls_in_its_cs_prereqs(self):
        p = plan(completed=FIRST_YEAR + ["STAT 2500"], include_core=False, extra_courses=["COMP 3200"],
                 terms=["Fall 2026", "Winter 2027", "Fall 2027"])
        placed = {c for t in p["terms"] for c in codes(t)}
        self.assertTrue({"COMP 2001", "COMP 2002", "COMP 3200"} <= placed)

    def test_terms_after_2026_27_are_flagged_as_assumed(self):
        done = FIRST_YEAR + ["COMP 2001", "COMP 2002", "STAT 2500"]
        p = plan(completed=done, include_core=False, extra_courses=["COMP 3200"], terms=["Fall 2027"])
        line = p["terms"][0]["courses"][0]
        self.assertEqual(line["code"], "COMP 3200")
        self.assertTrue(line["offering_assumed"])
        self.assertTrue(any("Fall 2026" in a or "2026-27" in a for a in p["assumptions"]))

    def test_course_not_offered_in_a_known_term_is_not_scheduled(self):
        done = FIRST_YEAR + ["COMP 2001", "COMP 2002", "STAT 2500"]
        p = plan(completed=done, include_core=False, extra_courses=["COMP 3200"], terms=["Winter 2027"])
        self.assertEqual([u["code"] for u in p["unplaced"]], ["COMP 3200"])
        self.assertIn("not offered", p["unplaced"][0]["reasons"][-1])

    def test_no_course_is_listed_twice_and_credits_add_up(self):
        for strategy in ("lightest", "fastest", "balanced"):
            p = plan(completed=FIRST_YEAR, strategy=strategy, electives_per_term=1,
                     terms=["Fall 2026", "Winter 2027", "Fall 2027", "Winter 2028"])
            all_codes = [c["code"] for t in p["terms"] for c in t["courses"]]
            self.assertEqual(len(all_codes), len(set(all_codes)), strategy)
            for t in p["terms"]:
                self.assertEqual(t["credit_hours"], sum(c["credit_hours"] for c in t["courses"]), strategy)

    def test_core_done_still_gets_cs_courses_and_diverse_electives(self):
        core_done = FIRST_YEAR + [f"COMP 200{i}" for i in range(1, 9)] + ["COMP 1600"]
        p = plan(completed=core_done, include_core=False, strategy="lightest", electives_per_term=3,
                 cs_electives_per_term=2, terms=["Fall 2026", "Winter 2027"])
        for t in p["terms"]:
            roles = [c["role"] for c in t["courses"]]
            self.assertEqual(roles.count("elective"), 3)
            self.assertGreaterEqual(roles.count("cs_elective"), 1)
            subjects = [c["code"].split()[0] for c in t["courses"] if c["role"] == "elective"]
            self.assertEqual(len(subjects), len(set(subjects)), "two electives from one subject in a term")
            self.assertLessEqual(t["credit_hours"], 15)
        self.assertEqual(p["terms"][0]["credit_hours"], 15)

    def test_unrated_electives_prefer_first_year_courses(self):
        p = plan(completed=FIRST_YEAR, include_core=False, electives_per_term=2, terms=["Fall 2026"])
        for c in p["terms"][0]["courses"]:
            self.assertEqual(int(c["code"].split()[1]) // 1000, 1)

    def test_elective_subject_filter(self):
        p = plan(completed=FIRST_YEAR, include_core=False, electives_per_term=2,
                 elective_subjects=["PSYC", "ANTH"], terms=["Fall 2026", "Winter 2027"])
        picked = {c["code"].split()[0] for t in p["terms"] for c in t["courses"]}
        self.assertEqual(picked, {"PSYC", "ANTH"})

    def test_interest_area_ranks_first(self):
        core_done = FIRST_YEAR + [f"COMP 200{i}" for i in range(1, 9)]
        p = plan(completed=core_done, include_core=False, cs_electives_per_term=1, interest_areas=["ToC"],
                 terms=["Fall 2026"])
        self.assertEqual(p["terms"][0]["courses"][0]["code"], "COMP 3602")

    def test_blocked_interest_courses_are_explained(self):
        core_done = FIRST_YEAR + [f"COMP 200{i}" for i in range(1, 9)]
        p = plan(completed=core_done, include_core=False, cs_electives_per_term=2, interest_areas=["AI"],
                 terms=["Fall 2026", "Winter 2027"])
        blocked = {b["code"]: b["reasons"] for b in p["interest_blocked"]}
        self.assertIn("COMP 3200", blocked)
        self.assertIn("STAT 2500", blocked["COMP 3200"][0])
        self.assertIn("MATH 2050", " ".join(blocked["COMP 3202"]))

    def test_interest_courses_appear_once_math_and_stat_are_done(self):
        done = FIRST_YEAR + [f"COMP 200{i}" for i in range(1, 9)] + ["STAT 2500", "MATH 2050"]
        p = plan(completed=done, include_core=False, cs_electives_per_term=2, interest_areas=["AI"],
                 terms=["Fall 2026"])
        self.assertEqual(codes(p["terms"][0]), {"COMP 3200", "COMP 3202"})
        self.assertEqual(p["interest_blocked"], [])

    def test_planner_schedules_stat_before_the_course_that_needs_it(self):
        done = FIRST_YEAR + ["COMP 2001", "COMP 2002"]
        p = plan(completed=done, include_core=False, extra_courses=["COMP 3200"],
                 terms=["Fall 2026", "Winter 2027", "Fall 2027"])
        where = {c["code"]: t["term"] for t in p["terms"] for c in t["courses"]}
        self.assertEqual(where["STAT 2500"], "Fall 2026")
        self.assertEqual(where["COMP 3200"], "Fall 2027")  # next time it runs after STAT 2500
        self.assertNotIn("MATH 1000", where)
        roles = {c["code"]: c["role"] for t in p["terms"] for c in t["courses"]}
        self.assertEqual(roles["STAT 2500"], "core")  # the degree requires it, so it is core, not just a prerequisite

    def test_the_calculus_chain_is_planned_for_math_2000(self):
        p = plan(completed=["COMP 1001"], include_core=False, extra_courses=["MATH 2000"],  # not yet admitted to the major
                 terms=["Fall 2026", "Winter 2027", "Spring 2027"])
        where = {c["code"]: t["term"] for t in p["terms"] for c in t["courses"]}
        self.assertEqual(where["MATH 1000"], "Fall 2026")
        self.assertEqual(where["MATH 1001"], "Winter 2027")
        self.assertEqual(where["MATH 2000"], "Spring 2027")

    def test_math_courses_are_spread_out_and_the_plan_says_so_when_terms_run_out(self):
        done = ["COMP 1001", "COMP 2001", "COMP 2002"]  # not admitted yet, so MATH 1000 is still to plan
        p = plan(completed=done, include_core=False, extra_courses=["COMP 3301"],
                 terms=["Fall 2026", "Winter 2027", "Spring 2027", "Fall 2027"])
        for term in p["terms"]:
            self.assertLessEqual(len(maths(term, "MATH")), 1)
        why = {u["code"]: " ".join(u["reasons"]) for u in p["unplaced"]}
        self.assertIn("COMP 3301", why)

    def test_math_courses_carry_their_usual_terms_not_an_instructor(self):
        self.assertTrue(OFFERED("STAT 2500", "Spring 2027")["offered"])
        self.assertFalse(OFFERED("MATH 2320", "Spring 2027")["offered"])
        self.assertIsNone(OFFERINGS["STAT 2500"]["Fall 2026"])

    def test_geography_2001_waits_for_geography_1050(self):
        p = plan(completed=FIRST_YEAR, include_core=False, electives_per_term=1, elective_subjects=["GEOG"],
                 terms=["Fall 2026", "Winter 2027"])
        where = {c["code"]: t["term"] for t in p["terms"] for c in t["courses"]}
        self.assertEqual(where["GEOG 1050"], "Fall 2026")  # no prerequisite, so first-year course first
        self.assertNotIn("GEOG 2001", {c for c in where if where[c] == "Fall 2026"})

    def test_an_elective_with_one_known_term_is_still_available_in_others(self):
        self.assertEqual(OFFERINGS["ANTH 1031"]["Fall 2026"], "D. Banoub")
        known = OFFERED("ANTH 1031", "Fall 2026")
        other = OFFERED("ANTH 1031", "Winter 2027")
        self.assertFalse(known["unknown"])
        self.assertTrue(other["offered"] and other["unknown"])

    def test_a_course_known_to_be_hard_is_not_in_the_lightest_plan(self):
        self.assertEqual(default_load(CATALOG["MATH 2000"]), 10.0)  # from data/load_overrides.csv
        self.assertEqual(default_load(CATALOG["MATH 2050"]), 7.0)   # other math keeps the flat guess
        done = FIRST_YEAR + ["MATH 1000", "MATH 1001"]
        p = plan(completed=done, strategy="lightest", credit_target=9, terms=["Fall 2026", "Winter 2027"])
        self.assertNotIn("MATH 2000", codes(p["terms"][0]))

    def test_one_math_and_one_stat_per_term_while_other_work_remains(self):
        p = plan(completed=FIRST_YEAR, terms=["Fall 2026", "Winter 2027", "Fall 2027", "Winter 2028"])
        for term in p["terms"][:2]:  # the COMP core is still being taken in these terms
            self.assertLessEqual(len(maths(term, "MATH")), 1)
            self.assertLessEqual(len(maths(term, "STAT")), 1)
        self.assertEqual(p["unplaced"], [])

    def test_several_math_courses_in_one_term_only_when_math_is_all_that_is_left(self):
        done = FIRST_YEAR + [f"COMP 200{i}" for i in range(1, 9)] + ["MATH 1000"]
        p = plan(completed=done, terms=["Fall 2026", "Winter 2027"])
        self.assertGreaterEqual(len(maths(p["terms"][0], "MATH")), 2)  # MATH 1001 and MATH 2050 together
        self.assertEqual(p["unplaced"], [])

    def test_statistics_waits_until_after_the_first_two_terms_for_an_early_student(self):
        p = plan(completed=FIRST_YEAR, terms=["Fall 2026", "Winter 2027", "Fall 2027", "Winter 2028", "Fall 2028"])
        where = {c["code"]: i for i, t in enumerate(p["terms"]) for c in t["courses"]}
        self.assertGreaterEqual(where["STAT 2500"], 2)
        self.assertEqual(p["unplaced"], [])

    def test_a_student_further_along_can_take_statistics_right_away(self):
        done = FIRST_YEAR + ["COMP 1600"] + [f"COMP 200{i}" for i in range(1, 9)]  # 30 credit hours done
        p = plan(completed=done, terms=["Fall 2026", "Winter 2027"])
        where = {c["code"]: i for i, t in enumerate(p["terms"]) for c in t["courses"]}
        self.assertEqual(where["STAT 2500"], 0)

    def test_statistics_is_used_in_an_early_term_rather_than_leaving_the_term_empty(self):
        p = plan(completed=["COMP 1001"], include_core=False, extra_courses=["STAT 2500"], terms=["Fall 2026"])
        self.assertEqual(codes(p["terms"][0]), {"STAT 2500"})

    def test_math_1000_is_assumed_done_once_a_student_is_in_the_major(self):
        p = plan(completed=FIRST_YEAR, terms=["Fall 2026", "Winter 2027", "Fall 2027", "Winter 2028"])
        placed = {c for t in p["terms"] for c in codes(t)}
        self.assertNotIn("MATH 1000", placed)
        self.assertTrue({"MATH 1001", "MATH 2000", "MATH 2050", "STAT 2500"} <= placed)
        self.assertEqual(p["unplaced"], [])
        self.assertTrue(any("MATH 1000 is assumed done" in a for a in p["assumptions"]))
        self.assertNotIn("MATH 1000", p["degree_progress"]["required_missing"])

    def test_a_new_student_still_gets_math_1000_planned(self):
        p = plan(completed=[], terms=["Fall 2026", "Winter 2027", "Fall 2027", "Winter 2028"])
        where = {c["code"]: i for i, t in enumerate(p["terms"]) for c in t["courses"]}
        self.assertEqual(where["MATH 1000"], 0)
        self.assertFalse(any("MATH 1000 is assumed done" in a for a in p["assumptions"]))

    def test_the_degree_math_is_part_of_the_core(self):
        p = plan(completed=[], terms=["Fall 2026", "Winter 2027", "Fall 2027", "Winter 2028", "Fall 2028"])
        placed = {c for t in p["terms"] for c in codes(t)}
        self.assertTrue({"MATH 1000", "MATH 1001", "MATH 2000", "MATH 2050", "STAT 2500"} <= placed)

    def test_alternatives_count_as_the_requirement(self):
        done = FIRST_YEAR + ["MATH 1006", "STAT 2550"]
        p = plan(completed=done, terms=["Fall 2026", "Winter 2027", "Fall 2027", "Winter 2028"])
        placed = {c for t in p["terms"] for c in codes(t)}
        self.assertNotIn("MATH 1000", placed)
        self.assertNotIn("STAT 2500", placed)
        self.assertNotIn("STAT 2550", placed)
        self.assertIn("MATH 1001", placed)  # MATH 1001 is still required

    def test_degree_progress_counts_hours_and_lists_what_is_missing(self):
        core_done = FIRST_YEAR + [f"COMP 200{i}" for i in range(1, 9)]
        p = plan(completed=core_done, include_core=False, terms=["Fall 2026"])
        prog = p["degree_progress"]
        self.assertEqual(prog["cs_hours"], {"have": 27, "need": 45})
        self.assertEqual(prog["upper_hours"]["have"], 0)
        self.assertEqual(prog["required_missing"], ["MATH 1001", "MATH 2000", "MATH 2050", "STAT 2500"])  # MATH 1000 is assumed

    def test_required_concentration_courses_rank_before_elective_ones(self):
        done = FIRST_YEAR + [f"COMP 200{i}" for i in range(1, 9)] + ["MATH 1000", "MATH 1001", "MATH 2000", "MATH 2050", "STAT 2500"]
        p = plan(completed=done, include_core=False, cs_electives_per_term=2, interest_areas=["VCG"], terms=["Fall 2026"])
        self.assertEqual(codes(p["terms"][0]), {"COMP 3300", "COMP 3301"})  # COMP 3200 is only an elective for VCG

    def test_credit_target_is_respected(self):
        p = plan(completed=FIRST_YEAR, credit_target=6)
        for t in p["terms"]:
            self.assertLessEqual(t["credit_hours"], 6)

    def test_electives_prefer_higher_ease(self):
        p = plan(completed=FIRST_YEAR, electives_per_term=1, ease_by_code={"PSYC 1000": 4.6, "BIOL 2040": 2.0})
        self.assertIn("PSYC 1000", codes(p["terms"][0]))

    def test_instructor_shown_for_known_terms(self):
        p = plan(completed=FIRST_YEAR)
        by_code = {c["code"]: c for c in p["terms"][0]["courses"]}
        self.assertEqual(by_code["COMP 2001"]["instructor"], "P. Patra")

    def test_no_acceptance_blocks_major_only_courses(self):
        p = plan(completed=FIRST_YEAR, accepted_into_major=False)
        self.assertEqual(comp(p["terms"][0]), set())

    def test_unknown_extra_code_is_reported(self):
        p = plan(completed=FIRST_YEAR, extra_courses=["COMP 9999"])
        self.assertEqual(p["unknown_codes"], ["COMP 9999"])

    def test_grade_warning(self):
        p = plan(completed=FIRST_YEAR, grades={"COMP 1001": 58})
        warns = [w for c in p["terms"][0]["courses"] for w in c["warnings"]]
        self.assertTrue(any("65%" in w for w in warns))


if __name__ == "__main__":
    unittest.main()
