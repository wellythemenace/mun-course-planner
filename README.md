# MUN Course Planner

A web app for Memorial University Computer Science students. It builds semester plans that respect
prerequisites and the 2026-27 degree rules, shows who is teaching what, and collects student ratings
(workload, ease, exams, marking) so people can pick lighter electives and avoid heavy terms.

**Stack:** Python (FastAPI, SQLite), React + TypeScript (Vite).

## What it does
- **Plan generator.** Pick the courses you have finished, the terms you want, credit hours per term and a
  strategy (lightest, balanced, fastest). The planner schedules prerequisites before the courses that need them,
  takes co-requisites in the same term, and explains anything it could not place.
- **Degree progress.** Shows your CS credit hours against the Major in Computer Science (45 CS credit hours, 18 at the
  3000/4000 level, 6 at the 4000 level, plus the required math and statistics) and lists what is still missing.
- **Concentrations.** Pick an area (AI, Data-centric Computing, Theory of Computation, Visual Computing and Games).
  Its required courses are ranked first, then its elective courses.
- **Electives browser.** No-prerequisite electives from Science, Anthropology and Geography, sorted by student ratings.
- **Professors.** Search a name and see the courses they teach and when, with a link to look up reviews elsewhere.
- **Ratings.** Students rate ease, hours per week, exam type, readings and marking for a class and professor.
  Averages are hidden until a course has 3 ratings, so a single opinion cannot decide anything.

## How the planner decides
- Each term it takes the courses whose prerequisites are done and that are offered, ranks them by the strategy,
  and fills up to the credit target.
- **Workload.** Hours per week come from student ratings once a course has 3. Until then it uses flat guesses by course
  type and level (my own rough numbers, not measured data). `backend/data/load_overrides.csv` lets you set a course by hand.
  Nine hours or more counts as heavy, and a term gets at most two heavy courses.
- **Math rules.** At most one MATH and one STAT course per term unless only math and stats are left. Statistics is kept
  out of the first two terms for a student with under 30 credit hours done. MATH 1000 is assumed done for a student who is
  in the major and past COMP 1001 and 1002, because admission requires it. Each assumption is listed in the plan.
- It is a greedy, rule-based planner on purpose: every placement can be explained, which matters more here than
  finding a mathematically optimal schedule.

## Run it
```
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```
API docs: http://localhost:8001/docs

Web app, in a second terminal:
```
cd frontend
npm install
npm run dev
```
Then open http://localhost:5173

## Tests
```
cd backend
PYTHONPATH=. python3 -m unittest discover -s tests -t . -v
```
The planner, prerequisite and data tests need no extra installs. The API tests run when FastAPI is installed
(`pip install -r requirements-dev.txt`) and are skipped otherwise.

## Where the data comes from
The 2026-27 University Calendar is the reference for course titles, prerequisites, program requirements and concentrations
(Computer Science section 11.4 and the course descriptions). When another page disagreed with the calendar, the calendar won.
- `backend/data/courses_2026_27.json`: 43 active COMP courses with prerequisites, co-requisites and concentration tags.
  Offerings and instructors come from the department's **tentative** 2026-27 list.
- `backend/data/math_stats_2026_27.json`: 12 math and statistics courses, with the department's usual offering pattern.
- `backend/data/electives_2026_27.json`: 32 electives. Each entry records its source and what is still unconfirmed.
- Add your own: `offerings_extra.csv` (who teaches what), `seed_ratings.csv` (starter ratings),
  `load_overrides.csv` (workload estimates). Restart the API after editing.

## Limits (read before trusting a plan)
- Offerings and instructors are **tentative**. Spring 2027 is not set, and terms after Winter 2027 reuse the 2026-27
  pattern and are flagged as assumed. Instructor names show as initial plus surname.
- Not modelled: admission to the major (competitive, with its own course requirements), honours programs, placement tests
  (treated as satisfied) and most minimum-grade rules (they only warn).
- Electives: offerings and instructors are not loaded, credit hours are assumed to be 3, and only Science, Anthropology and
  Geography are covered. Some entries are flagged "needs review".
- There are no logins. A browser can rate a course once, which is not abuse-proof, so a public launch would need accounts and
  moderation.
- Review links open a search elsewhere. Reviews from other sites are deliberately not copied or scraped.
- The official University Calendar and an academic advisor have the final say.

## Ideas for later
- A "My semesters" log so students record what they took and rate it after the term ends.
- More Humanities and Social Sciences departments, and offering data for electives.
- Accounts and moderation, then a deployed demo.
