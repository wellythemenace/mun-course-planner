import type {
  CourseDetail, CourseSummary, PlanRequest, PlanResult, Professor, RatingInput,
} from "./types";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    throw new Error(typeof detail === "string" ? detail : "That request was not valid. Check what you entered.");
  }
  return res.json() as Promise<T>;
}

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === "" || v === false) continue;
    p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

function makeId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : String(Math.random()).slice(2) + String(Date.now());
}

const memoryId = makeId();

// One anonymous id per browser, so a person can rate a course once (re-rating updates it).
export function clientId(): string {
  try {
    let id = localStorage.getItem("clientId");
    if (!id) {
      id = makeId();
      localStorage.setItem("clientId", id);
    }
    return id;
  } catch {
    return memoryId;
  }
}

export const api = {
  courses: (p: { q?: string; kind?: string; term?: string }) =>
    request<CourseSummary[]>(`/courses${qs({ ...p, limit: 300 })}`),
  outside: () => request<{ code: string; needed_by: string[] }[]>("/outside-courses"),
  course: (code: string) => request<CourseDetail>(`/courses/${encodeURIComponent(code)}`),
  electives: (p: { q?: string; term?: string }) => request<CourseSummary[]>(`/electives${qs(p)}`),
  professors: (p: { q?: string; term?: string }) => request<Professor[]>(`/professors${qs(p)}`),
  plan: (body: PlanRequest) =>
    request<PlanResult>("/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  rate: (body: RatingInput) =>
    request<{ saved: boolean }>("/ratings", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Client-Id": clientId() },
      body: JSON.stringify(body),
    }),
};
