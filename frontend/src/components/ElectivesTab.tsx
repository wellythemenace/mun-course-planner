import { useEffect, useState } from "react";
import { api } from "../api";
import type { CourseSummary, OpenCourse } from "../types";
import CourseList from "./CourseList";

export default function ElectivesTab({ onOpen }: { onOpen: OpenCourse }) {
  const [q, setQ] = useState("");
  const [term, setTerm] = useState("");
  const [items, setItems] = useState<CourseSummary[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const t = setTimeout(() => {
      api.electives({ q, term: term || undefined })
        .then((r) => { setItems(r); setError(""); })
        .catch((e: Error) => setError(e.message));
    }, 200);
    return () => clearTimeout(t);
  }, [q, term]);

  return (
    <section className="panel">
      <h2>Find an elective</h2>
      <p className="muted">
        Electives with no prerequisites from the Faculty of Science list. Courses with enough student ratings come
        first, easiest on top. Rate the ones you have taken so this gets better for everyone.
      </p>
      <div className="row">
        <input placeholder="Search by name or code" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={term} onChange={(e) => setTerm(e.target.value)}>
          <option value="">Any term</option>
          <option>Fall 2026</option>
          <option>Winter 2027</option>
          <option>Spring 2027</option>
        </select>
      </div>
      {error && <div className="error">{error}</div>}
      <CourseList items={items} onOpen={onOpen} />
    </section>
  );
}
