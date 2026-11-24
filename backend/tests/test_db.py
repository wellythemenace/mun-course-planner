import os
import tempfile
import unittest

_tmp = tempfile.mkdtemp()
os.environ["PLANNER_DB"] = os.path.join(_tmp, "t.db")

from app import db  # noqa: E402


class DbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()

    def test_catalog_loaded(self):
        with db.session() as c:
            catalog, offerings = db.load_catalog(c)
        self.assertIn("COMP 2001", catalog)
        self.assertIn("PSYC 1000", catalog)
        self.assertEqual(catalog["PSYC 1000"]["kind"], "elective")
        self.assertEqual(offerings["COMP 2005"]["Fall 2026"], "M. Hatcher")

    def test_professor_added_from_the_csv_is_searchable(self):
        with db.session() as c:
            row = c.execute("SELECT name, department FROM instructors WHERE name = 'D. Banoub'").fetchone()
            courses = [r[0] for r in c.execute("SELECT course_code FROM offerings WHERE instructor = 'D. Banoub'")]
        self.assertEqual(row["department"], "Anthropology")
        self.assertEqual(courses, ["ANTH 1031"])

    def test_core_courses_by_year(self):
        with db.session() as c:
            catalog, _ = db.load_catalog(c)
        core = {code for code, v in catalog.items() if v["required_for_major"] and v["kind"] == "cs"}
        self.assertEqual({x for x in core if catalog[x]["level"] == 1000}, {"COMP 1001", "COMP 1002", "COMP 1003"})
        self.assertEqual({x for x in core if catalog[x]["level"] == 2000}, {f"COMP 200{i}" for i in range(1, 9)})
        self.assertEqual(sum(catalog[x]["credit_hours"] for x in core), 27)
        math = {code for code, v in catalog.items() if v["required_for_major"] and v["kind"] == "support"}
        self.assertEqual(math, {"MATH 1000", "MATH 1001", "MATH 2000", "MATH 2050", "STAT 2500"})
        self.assertEqual(catalog["MATH 1000"]["alternatives"], ["MATH 1006"])
        self.assertEqual(catalog["COMP 4300"]["concentrations"]["VCG"], "required")
        self.assertEqual(catalog["COMP 3200"]["concentrations"], {"AI": "required", "VCG": "elective"})

    def test_professor_lookup(self):
        with db.session() as c:
            rows = c.execute(
                "SELECT o.course_code FROM offerings o WHERE o.instructor = 'M. Hatcher' ORDER BY 1").fetchall()
        self.assertIn("COMP 2005", [r[0] for r in rows])
        self.assertIn("COMP 4754", [r[0] for r in rows])

    def test_rating_summary_hidden_until_enough(self):
        with db.session() as c:
            for i in range(2):
                c.execute("INSERT INTO ratings (course_code, ease, client_id) VALUES ('PSYC 1000', 4, ?)", (f"client-{i}-xxxx",))
            s = db.rating_summary(c, code="PSYC 1000")
            self.assertFalse(s["enough"])
            self.assertNotIn("avg_ease", s)
            c.execute("INSERT INTO ratings (course_code, ease, workload_hours, client_id) VALUES ('PSYC 1000', 5, 4, 'client-3-xxxx')")
            s = db.rating_summary(c, code="PSYC 1000")
            self.assertTrue(s["enough"])
            self.assertEqual(s["avg_ease"], 4.33)

    def test_one_rating_per_client_per_course(self):
        with db.session() as c:
            c.execute("INSERT INTO ratings (course_code, ease, client_id) VALUES ('BIOL 2040', 3, 'same-client-1')")
            with self.assertRaises(Exception):
                c.execute("INSERT INTO ratings (course_code, ease, client_id) VALUES ('BIOL 2040', 5, 'same-client-1')")


if __name__ == "__main__":
    unittest.main()
