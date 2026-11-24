import { useEffect, useState } from "react";
import { api } from "../api";
import type { OpenCourse, Professor } from "../types";
import RatingBadge from "./RatingBadge";
import { ProfessorReviewLink } from "./ExternalLinks";

function groupByTerm(p: Professor): [string, Professor["offerings"]][] {
  const map = new Map<string, Professor["offerings"]>();
  for (const o of p.offerings) map.set(o.term, [...(map.get(o.term) ?? []), o]);
  return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
}

// One entry per course the professor teaches, with the terms they teach it.
function coursesOf(p: Professor): { code: string; title: string; terms: string[] }[] {
  const map = new Map<string, { code: string; title: string; terms: string[] }>();
  for (const o of p.offerings) {
    const entry = map.get(o.course_code) ?? { code: o.course_code, title: o.title, terms: [] };
    if (!entry.terms.includes(o.term)) entry.terms.push(o.term);
    map.set(o.course_code, entry);
  }
  return [...map.values()];
}

export default function ProfessorsTab({ onOpen }: { onOpen: OpenCourse }) {
  const [q, setQ] = useState("");
  const [term, setTerm] = useState("");
  const [items, setItems] = useState<Professor[]>([]);
  const [error, setError] = useState("");
  const [menuFor, setMenuFor] = useState<number | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      api.professors({ q, term: term || undefined })
        .then((r) => { setItems(r); setError(""); })
        .catch((e: Error) => setError(e.message));
    }, 200);
    return () => clearTimeout(t);
  }, [q, term]);

  // Close the course menu on any outside click or Escape.
  useEffect(() => {
    if (menuFor === null) return;
    const close = () => setMenuFor(null);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    document.addEventListener("click", close);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("click", close);
      window.removeEventListener("keydown", onKey);
    };
  }, [menuFor]);

  function rate(p: Professor, c: { code: string; terms: string[] }) {
    setMenuFor(null);
    onOpen(c.code, { rate: true, instructor: p.name, term: c.terms.length === 1 ? c.terms[0] : undefined });
  }

  return (
    <section className="panel">
      <h2>Who is teaching what</h2>
      <p className="muted">
        From the Department of Computer Science's tentative 2026-27 list. Names appear as the department lists them
        (initial and surname). Other departments are not loaded yet.
      </p>
      <div className="row">
        <input placeholder="Search a professor's name" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={term} onChange={(e) => setTerm(e.target.value)}>
          <option value="">Any term</option>
          <option>Fall 2026</option>
          <option>Winter 2027</option>
        </select>
      </div>
      {error && <div className="error">{error}</div>}
      {items.length === 0 && <p className="muted">No professor matches.</p>}
      {items.map((p) => {
        const courses = coursesOf(p);
        return (
          <div key={p.id} className="card">
            <div className="card-head">
              <strong>{p.name}</strong>
              <span className="right">
                <span className="muted small">{p.department}</span>
                <span className="rate-wrap">
                  <button
                    className="rate-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (courses.length === 1) rate(p, courses[0]);
                      else setMenuFor(menuFor === p.id ? null : p.id);
                    }}
                  >
                    Rate{courses.length > 1 ? " ▾" : ""}
                  </button>
                  {menuFor === p.id && (
                    <div className="rate-menu" onClick={(e) => e.stopPropagation()}>
                      <div className="muted small rate-menu-title">Which class?</div>
                      {courses.map((c) => (
                        <button key={c.code} onClick={() => rate(p, c)}>
                          <strong>{c.code}</strong> {c.title}
                          <span className="muted small"> · {c.terms.join(", ")}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </span>
              </span>
            </div>
            {p.rating.enough && <div className="small"><RatingBadge rating={p.rating} /></div>}
            {groupByTerm(p).map(([t, offerings]) => (
              <div key={t} className="small">
                <span className="muted">{t}: </span>
                {offerings.map((o, i) => (
                  <span key={o.course_code}>
                    {i > 0 && ", "}
                    <button className="link" onClick={() => onOpen(o.course_code)}>{o.course_code}</button> {o.title}
                  </span>
                ))}
              </div>
            ))}
            <ProfessorReviewLink name={p.name} />
          </div>
        );
      })}
    </section>
  );
}
