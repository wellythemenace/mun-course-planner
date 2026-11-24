import os
import tempfile
import unittest

_tmp = tempfile.mkdtemp()
os.environ["PLANNER_DB"] = os.path.join(_tmp, "api.db")

try:
    from fastapi.testclient import TestClient
    from app.main import app
except ImportError:  # fastapi/httpx not installed
    raise unittest.SkipTest("fastapi and httpx are required for API tests")

client = TestClient(app)


class ApiTests(unittest.TestCase):
    def test_courses_and_filters(self):
        r = client.get("/api/courses", params={"q": "data structures"})
        self.assertEqual([c["code"] for c in r.json()], ["COMP 2002"])
        electives = client.get("/api/courses", params={"kind": "elective"}).json()
        self.assertTrue(all(c["kind"] == "elective" for c in electives))

    def test_course_detail_has_offerings_and_404(self):
        d = client.get("/api/courses/comp 2005").json()
        self.assertIn("M. Hatcher", [o["instructor"] for o in d["offerings"]])
        self.assertEqual(client.get("/api/courses/COMP 9999").status_code, 404)

    def test_professor_search(self):
        r = client.get("/api/professors", params={"q": "hatcher"}).json()
        self.assertEqual(len(r), 1)
        self.assertIn("COMP 2005", [o["course_code"] for o in r[0]["offerings"]])
        one = client.get(f"/api/professors/{r[0]['id']}").json()
        self.assertEqual(one["name"], "M. Hatcher")

    def test_rating_needs_client_id_and_validates(self):
        body = {"course_code": "PSYC 1000", "ease": 4}
        self.assertEqual(client.post("/api/ratings", json=body).status_code, 400)
        h = {"X-Client-Id": "client-abcdef"}
        self.assertEqual(client.post("/api/ratings", json={"course_code": "PSYC 1000", "ease": 9}, headers=h).status_code, 422)
        self.assertEqual(client.post("/api/ratings", json={"course_code": "NOPE 1000", "ease": 3}, headers=h).status_code, 404)

    def test_ratings_become_visible_after_three_and_rerating_updates(self):
        for i in range(3):
            r = client.post("/api/ratings", json={"course_code": "BIOL 2041", "ease": 4, "workload_hours": 3},
                            headers={"X-Client-Id": f"client-{i}-abcdef"})
            self.assertEqual(r.status_code, 201)
        e = client.get("/api/electives").json()
        self.assertEqual(e[0]["code"], "BIOL 2041")
        self.assertEqual(e[0]["rating"]["avg_ease"], 4.0)
        client.post("/api/ratings", json={"course_code": "BIOL 2041", "ease": 1},
                    headers={"X-Client-Id": "client-0-abcdef"})
        self.assertEqual(client.get("/api/courses/BIOL 2041").json()["rating"]["count"], 3)

    def test_plan_endpoint(self):
        r = client.post("/api/plan", json={"completed": ["comp 1001", "COMP 1002", "COMP 1003"],
                                           "terms": ["Fall 2026", "Winter 2027"]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["terms"]), 2)
        self.assertEqual(client.post("/api/plan", json={"terms": ["Autumn 2026"]}).status_code, 422)

    def test_eligibility(self):
        r = client.post("/api/courses/COMP 3301/eligibility", json={"completed": ["COMP 2002"]}).json()
        self.assertFalse(r["eligible"])
        self.assertEqual(r["missing"], ["MATH 2000", "MATH 2050"])


if __name__ == "__main__":
    unittest.main()
