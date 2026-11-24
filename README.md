# MUN Course Planner

Plan a Computer Science degree at Memorial University: see which courses are offered each
semester, find lighter electives from student ratings, look up what a professor is teaching,
and build semester plans that respect prerequisites.

**Status:** backend, data and web UI written. Needs a first run on your machine.

## What it does
- **Course catalog:** 43 active COMP courses (2026-27 calendar) plus no-prerequisite electives from the Faculty of Science list.
- **Professor search:** type a name, see the courses they teach and when.
- **Ratings:** students rate ease, weekly workload, exam type, readings and marking. Averages show only after 3 ratings so a single opinion cannot mislead.
- **Plan generator:** pick completed courses, terms, credits per term and a strategy (lightest, balanced, fastest). Co-requisites are scheduled together, and prerequisites always come in an earlier term.

## Run it
```
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```
Open http://localhost:8001/docs to try every endpoint.

Web app (second terminal):
```
cd frontend
npm install
npm run dev
```
Then open http://localhost:5173

Tests (no extra installs needed for the logic tests):
```
cd backend
PYTHONPATH=. python3 -m unittest discover -s tests -t . -v
```
For the API tests too: `pip install -r requirements-dev.txt`.

## Adding data
- `backend/data/offerings_extra.csv`: who teaches what, and when (e.g. for electives).
- `backend/data/seed_ratings.csv`: starter ratings from people who took the course.
- `backend/data/electives_2026_27.json`: more electives.
Restart the API after editing.

## Limits (read before trusting a plan)
- Offerings and instructors come from the department's **tentative** 2026-27 list (instructor names appear as initials plus surname). Spring 2027 is not set. Terms after Winter 2027 reuse the 2026-27 pattern and are flagged as assumed.
- "Required for the major" covers only the department's core-course markers, not full degree rules (credit totals, math/stat, electives, 4000-level concentration courses).
- First-year math and the math/statistics courses CS courses name (MATH 1000 to 2320, STAT 2500/2550) are loaded from the 2026-27 calendar, with the Department of Mathematics and Statistics' usual offering pattern. Placement-test alternatives are assumed satisfied. BIOL 1001 and ECE 7410 are not loaded and count only if you list them as completed.
- Elective offerings and instructors are not loaded yet. Elective credit hours are assumed to be 3.
- There are no logins. One person can rate a course once per browser, which is not abuse-proof. Add moderation before a public launch.
- The official University Calendar and an academic advisor have the final say.
