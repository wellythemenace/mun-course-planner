import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import type { CourseDetail, RatingInput } from "../types";

export default function RatingForm({ course, onSaved, initialInstructor, initialTerm }: {
  course: CourseDetail; onSaved: () => void; initialInstructor?: string; initialTerm?: string;
}) {
  const [ease, setEase] = useState("");
  const [hours, setHours] = useState("");
  const [assessments, setAssessments] = useState("");
  const [exam, setExam] = useState("");
  const [readings, setReadings] = useState("");
  const [marking, setMarking] = useState("");
  const [instructor, setInstructor] = useState(initialInstructor ?? "");
  const [term, setTerm] = useState(initialTerm ?? "");
  const [comment, setComment] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const instructors = [...new Set([...(initialInstructor ? [initialInstructor] : []),
    ...course.offerings.map((o) => o.instructor).filter((x): x is string => !!x)])];
  const terms = [...new Set(course.offerings.map((o) => o.term))];

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");
    if (!ease) {
      setError("Pick an ease score from 1 to 5.");
      return;
    }
    const body: RatingInput = { course_code: course.code, ease: Number(ease) };
    if (hours) body.workload_hours = Number(hours);
    if (assessments) body.assessments = Number(assessments);
    if (exam) body.exam_type = exam as RatingInput["exam_type"];
    if (readings) body.readings = readings as RatingInput["readings"];
    if (marking) body.marking = marking as RatingInput["marking"];
    if (instructor) body.instructor = instructor;
    if (term) body.term = term;
    if (comment.trim()) body.comment = comment.trim();
    try {
      await api.rate(body);
      setMessage("Saved. Thank you. Rating again later updates your rating.");
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your rating.");
    }
  }

  return (
    <form onSubmit={submit} className="rating-form">
      <h3>Rate this course</h3>
      <p className="muted small">Anonymous. Only rate courses you took. Describe the course, and keep it fair and respectful.</p>
      <div className="grid2">
        <div className="field">
          <label>How easy was it? (1 hard, 5 easy)</label>
          <select value={ease} onChange={(e) => setEase(e.target.value)}>
            <option value="">Choose…</option>
            {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Hours per week (optional)</label>
          <input type="number" min={0} max={40} value={hours} onChange={(e) => setHours(e.target.value)} />
        </div>
        <div className="field">
          <label>Number of assessments (optional)</label>
          <input type="number" min={0} max={30} value={assessments} onChange={(e) => setAssessments(e.target.value)} />
        </div>
        <div className="field">
          <label>Exams</label>
          <select value={exam} onChange={(e) => setExam(e.target.value)}>
            <option value="">Not sure</option>
            <option value="none">No exam</option>
            <option value="take_home">Take-home</option>
            <option value="in_person">In person</option>
            <option value="mixed">Mix</option>
          </select>
        </div>
        <div className="field">
          <label>Reading load</label>
          <select value={readings} onChange={(e) => setReadings(e.target.value)}>
            <option value="">Not sure</option>
            <option value="light">Light</option>
            <option value="medium">Medium</option>
            <option value="heavy">Heavy</option>
          </select>
        </div>
        <div className="field">
          <label>Marking</label>
          <select value={marking} onChange={(e) => setMarking(e.target.value)}>
            <option value="">Not sure</option>
            <option value="lenient">Lenient</option>
            <option value="fair">Fair</option>
            <option value="harsh">Harsh</option>
          </select>
        </div>
        <div className="field">
          <label>Who taught it (optional)</label>
          {instructors.length > 0 ? (
            <select value={instructor} onChange={(e) => setInstructor(e.target.value)}>
              <option value="">Not sure</option>
              {instructors.map((i) => <option key={i}>{i}</option>)}
            </select>
          ) : (
            <input maxLength={80} placeholder="e.g. D. Banoub" value={instructor}
              onChange={(e) => setInstructor(e.target.value)} />
          )}
        </div>
        {terms.length > 0 && (
          <div className="field">
            <label>Term (optional)</label>
            <select value={term} onChange={(e) => setTerm(e.target.value)}>
              <option value="">Not sure</option>
              {terms.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
        )}
      </div>
      <div className="field">
        <label>Comment (optional, up to 500 characters)</label>
        <textarea maxLength={500} value={comment} onChange={(e) => setComment(e.target.value)} />
      </div>
      <button className="primary" type="submit">Submit rating</button>
      {message && <div className="ok">{message}</div>}
      {error && <div className="error">{error}</div>}
    </form>
  );
}
