import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { CourseDetail } from "../types";
import RatingBadge from "./RatingBadge";
import RatingForm from "./RatingForm";
import { CourseReviewLink } from "./ExternalLinks";

function counts(label: string, data?: Record<string, number>) {
  if (!data || Object.keys(data).length === 0) return null;
  return (
    <div className="small">
      <span className="muted">{label}: </span>
      {Object.entries(data).map(([k, v]) => `${k.replace("_", " ")} (${v})`).join(", ")}
    </div>
  );
}

export default function CourseDrawer({ code, rate, instructor, term, onClose }: {
  code: string; rate?: boolean; instructor?: string; term?: string; onClose: () => void;
}) {
  const formRef = useRef<HTMLDivElement>(null);
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.course(code).then(setCourse).catch((e: Error) => setError(e.message));
  }, [code]);

  useEffect(() => {
    setCourse(null);
    setError("");
    load();
  }, [load]);

  // Opened with the Rate button: scroll to the rating form once the course has loaded.
  useEffect(() => {
    if (!rate || !course) return;
    const t = setTimeout(() => formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
    return () => clearTimeout(t);
  }, [rate, course?.code]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="overlay" onClick={onClose}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()}>
        <button className="close" onClick={onClose} aria-label="Close">×</button>
        {error && <div className="error">{error}</div>}
        {!course && !error && <p className="muted">Loading…</p>}
        {course && (
          <>
            <h2>{course.code}</h2>
            <h3>{course.title}</h3>
            <div className="muted small">
              {course.credit_hours} credit hours
              {course.required_for_major ? " · required for the CS major" : ""}
              {course.concentration ? ` · concentration: ${course.concentration}` : ""}
            </div>
            <p><strong>Prerequisites:</strong> {course.prereq_text}</p>
            {course.coreq.length > 0 && <p><strong>Take together with:</strong> {course.coreq.join(", ")}</p>}
            {course.requires_program_acceptance && (
              <p className="small"><strong>Program acceptance needed:</strong> {course.requires_program_acceptance}</p>
            )}
            {course.note && <p className="muted small">{course.note}</p>}
            {course.needs_review && <div className="warn small">Check this entry: {course.needs_review}</div>}

            <h3>When and who</h3>
            {course.offerings.length === 0 && <p className="muted small">No offering data loaded for this course.</p>}
            {course.offerings.map((o) => (
              <div key={o.term + o.instructor} className="small">{o.term}: {o.instructor ?? "instructor not listed"}</div>
            ))}
            <p className="muted small">Tentative 2026-27 department list. Confirm in the registrar's schedule.</p>

            <h3>Student ratings</h3>
            <div><RatingBadge rating={course.rating} /></div>
            {counts("Exams", course.rating.exam_types)}
            {counts("Readings", course.rating.readings)}
            {counts("Marking", course.rating.marking)}
            {course.recent_comments.map((c, i) => (
              <div key={i} className="comment small">
                <strong>Ease {c.ease}/5</strong>{c.term ? ` · ${c.term}` : ""}{c.source === "seed" ? " · starter rating" : ""}
                <div>{c.comment}</div>
              </div>
            ))}

            <CourseReviewLink code={course.code} />

            <div ref={formRef}><RatingForm course={course} onSaved={load} initialInstructor={instructor} initialTerm={term} /></div>
          </>
        )}
      </aside>
    </div>
  );
}
