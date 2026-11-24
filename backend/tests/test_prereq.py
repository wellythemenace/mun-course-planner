import unittest

from app import db
from app.prereq import is_satisfied, missing, normalize_code, outside_requirements

CATALOG, _ROWS, _WARN = db.catalog_from_files()


class PrereqTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize_code("  comp   2001 "), "COMP 2001")

    def test_none_and_single(self):
        self.assertTrue(is_satisfied(None, set(), CATALOG))
        self.assertFalse(is_satisfied("COMP 1001", set(), CATALOG))
        self.assertTrue(is_satisfied("COMP 1001", {"COMP 1001"}, CATALOG))

    def test_all_any(self):
        req = {"all": ["A 1000", {"any": ["B 1000", "C 1000"]}]}
        self.assertFalse(is_satisfied(req, {"A 1000"}, {}))
        self.assertTrue(is_satisfied(req, {"A 1000", "C 1000"}, {}))

    def test_credits_from(self):
        req = {"credits_from": {"subject": "COMP", "min_level": 3000, "hours": 6}}
        self.assertFalse(is_satisfied(req, {"COMP 3200"}, CATALOG))
        self.assertTrue(is_satisfied(req, {"COMP 3200", "COMP 3202"}, CATALOG))
        self.assertFalse(is_satisfied(req, {"COMP 2001", "COMP 2002"}, CATALOG))

    def test_missing_is_readable(self):
        out = missing(CATALOG["COMP 3301"]["prereq"], {"COMP 2002"}, CATALOG)
        self.assertEqual(out, ["MATH 2000", "MATH 2050"])

    def test_real_course_comp_2001(self):
        req = CATALOG["COMP 2001"]["prereq"]
        self.assertTrue(is_satisfied(req, {"COMP 1001", "COMP 1002", "COMP 1003"}, CATALOG))
        self.assertTrue(is_satisfied(req, {"COMP 1001", "MATH 2320", "COMP 1003"}, CATALOG))
        self.assertFalse(is_satisfied(req, {"COMP 1001", "COMP 1002"}, CATALOG))

    def test_outside_requirements_explain_where_they_come_from(self):
        out = outside_requirements(CATALOG)
        self.assertEqual(out["BIOL 1001"], ["COMP 3550"])
        self.assertNotIn("MATH 1000", out)  # no CS course names it directly
        for loaded in ("MATH 2000", "MATH 2050", "MATH 2320", "STAT 2500", "STAT 2550"):
            self.assertNotIn(loaded, out)  # now in the catalog as math courses
        self.assertEqual(set(out), {"BIOL 1001", "ECE 7410"})
        self.assertNotIn("COMP 2001", out)  # catalog courses are not "outside"

    def test_math_and_stat_prerequisites_match_the_calendar(self):
        self.assertEqual(CATALOG["STAT 2500"]["title"], "Statistical Foundations for Data Analytics")
        self.assertIsNone(CATALOG["STAT 2500"]["prereq"])  # 3 credit hours or placement, assumed met
        stat2550 = CATALOG["STAT 2550"]["prereq"]
        self.assertFalse(is_satisfied(stat2550, set(), CATALOG))
        self.assertTrue(is_satisfied(stat2550, {"MATH 1000"}, CATALOG))
        self.assertTrue(is_satisfied(stat2550, {"MATH 1006"}, CATALOG))
        self.assertEqual(CATALOG["MATH 2000"]["prereq"], "MATH 1001")
        math2320 = CATALOG["MATH 2320"]["prereq"]
        self.assertTrue(is_satisfied(math2320, {"MATH 2050"}, CATALOG))
        self.assertTrue(is_satisfied(math2320, {"MATH 1001"}, CATALOG))
        self.assertFalse(is_satisfied(math2320, {"MATH 1000"}, CATALOG))
        self.assertEqual(CATALOG["STAT 1510"]["coreq"], ["MATH 1000"])

    def test_every_course_evaluates(self):
        for code, c in CATALOG.items():
            is_satisfied(c["prereq"], set(), CATALOG)  # must not raise


if __name__ == "__main__":
    unittest.main()
