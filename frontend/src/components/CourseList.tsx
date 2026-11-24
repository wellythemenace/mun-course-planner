import type { CourseSummary, OpenCourse } from "../types";
import RatingBadge from "./RatingBadge";

export default function CourseList({ items, onOpen }: { items: CourseSummary[]; onOpen: OpenCourse }) {
  if (items.length === 0) return <p className="muted">Nothing matches.</p>;
  return (
    <div>
      {items.map((c) => (
        <div key={c.code} className="card">
          <div className="card-head">
            <button className="link strong" onClick={() => onOpen(c.code)}>{c.code}</button>
            <span className="right">
              <span className="muted small">{c.credit_hours} CH</span>
              <button className="rate-btn" onClick={() => onOpen(c.code, { rate: true })}>Rate</button>
            </span>
          </div>
          <div>{c.title}</div>
          <div className="small"><RatingBadge rating={c.rating} /></div>
          <div className="muted small">
            {c.offered_terms.length > 0 ? `Offered: ${c.offered_terms.join(", ")}` : "Offering not loaded"}
            {" · Prerequisites: "}{c.prereq_text}
          </div>
          {c.needs_review && <div className="warn small">Check this entry: {c.needs_review}</div>}
        </div>
      ))}
    </div>
  );
}
