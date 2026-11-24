import { useEffect, useState } from "react";
import { api } from "../api";
import type { CourseSummary, OpenCourse } from "../types";
import CourseList from "./CourseList";

export default function CoursesTab({ onOpen }: { onOpen: OpenCourse }) {
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("");
  const [term, setTerm] = useState("");
  const [items, setItems] = useState<CourseSummary[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const t = setTimeout(() => {
      api.courses({ q, kind: kind || undefined, term: term || undefined })
        .then((r) => { setItems(r); setError(""); })
        .catch((e: Error) => setError(e.message));
    }, 200);
    return () => clearTimeout(t);
  }, [q, kind, term]);

  return (
    <section className="panel">
      <h2>All courses</h2>
      <div className="row">
        <input placeholder="Search by name or code" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="">CS and electives</option>
          <option value="cs">CS only</option>
          <option value="elective">Electives only</option>
          <option value="support">Math and statistics only</option>
        </select>
        <select value={term} onChange={(e) => setTerm(e.target.value)}>
          <option value="">Any term</option>
          <option>Fall 2026</option>
          <option>Winter 2027</option>
        </select>
      </div>
      {error && <div className="error">{error}</div>}
      <CourseList items={items} onOpen={onOpen} />
    </section>
  );
}
