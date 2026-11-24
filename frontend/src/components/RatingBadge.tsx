import type { RatingSummary } from "../types";

export default function RatingBadge({ rating }: { rating: RatingSummary }) {
  if (!rating.enough) {
    const left = rating.min_needed - rating.count;
    return (
      <span className="muted">
        No score yet: needs {left} more rating{left === 1 ? "" : "s"} ({rating.count} so far)
      </span>
    );
  }
  const hours = rating.avg_workload_hours != null ? ` · about ${rating.avg_workload_hours} h/wk` : "";
  return (
    <span className="badge">
      Ease {rating.avg_ease?.toFixed(1)}/5{hours} · {rating.count} ratings
    </span>
  );
}
