import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { CourseSummary, PlanCourse, PlanResult, Strategy } from "../types";
import CheckboxDropdown from "./CheckboxDropdown";
import type { Option } from "./CheckboxDropdown";

const TERM_OPTIONS = [
  "Fall 2026", "Winter 2027", "Spring 2027", "Fall 2027", "Winter 2028", "Spring 2028", "Fall 2028", "Winter 2029",
];
const INTERESTS = [
  { id: "AI", label: "Artificial intelligence" },
  { id: "VCG", label: "Visual computing and games" },
  { id: "DcC", label: "Data-centric computing" },
  { id: "ToC", label: "Theory of computation" },
];
const SUBJECT_NAMES: Record<string, string> = {
  ANTH: "Anthropology", BIOL: "Biology", EASC: "Earth Sciences", FOLK: "Folklore", GEOG: "Geography", HUBI: "Human Biosciences",
  OCSC: "Ocean Sciences", PSYC: "Psychology", SCWK: "Social Work",
};
const ROLE_LABELS: Record<PlanCourse["role"], string> = {
  core: "CS core", chosen: "chosen", cs_elective: "CS elective", elective: "elective", prereq: "prerequisite",
};

export default function PlanTab({ onOpen }: { onOpen: (code: string) => void }) {
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [outside, setOutside] = useState<{ code: string; needed_by: string[] }[]>([]);
  const [completed, setCompleted] = useState<string[]>([]);
  const [extras, setExtras] = useState<string[]>([]);
  const [terms, setTerms] = useState<string[]>(["Fall 2026", "Winter 2027"]);
  const [creditTarget, setCreditTarget] = useState(15);
  const [strategy, setStrategy] = useState<Strategy>("balanced");
  const [electives, setElectives] = useState(0);
  const [csElectives, setCsElectives] = useState(1);
  const [interests, setInterests] = useState<string[]>([]);
  const [subjects, setSubjects] = useState<string[]>([]);
  const [accepted, setAccepted] = useState(true);
  const [core, setCore] = useState(true);
  const [result, setResult] = useState<PlanResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.courses({}).then(setCourses).catch(() => setCourses([]));
    api.outside().then(setOutside).catch(() => setOutside([]));
  }, []);

  const csOptions: Option[] = useMemo(
    () => courses.filter((c) => c.kind === "cs")
      .map((c) => ({ value: c.code, label: `${c.code} ${c.title}`, group: `COMP ${c.level}-level` })),
    [courses]);
  const completedOptions: Option[] = useMemo(
    () => [
      ...csOptions,
      ...courses.filter((c) => c.kind === "elective")
        .map((c) => ({ value: c.code, label: `${c.code} ${c.title}`, group: "Electives" })),
      ...courses.filter((c) => c.kind === "support")
        .map((c) => ({ value: c.code, label: `${c.code} ${c.title}`, group: "Math and statistics" })),
      ...outside.map((o) => ({
        value: o.code,
        label: `${o.code} · needed for ${o.needed_by.slice(0, 4).join(", ")}${o.needed_by.length > 4 ? " and more" : ""}`,
        group: "Other courses CS courses require (not loaded)",
      })),
    ],
    [courses, csOptions, outside]);
  const subjectOptions: Option[] = useMemo(
    () => [...new Set(courses.filter((c) => c.kind === "elective").map((c) => c.subject))].sort()
      .map((s) => ({ value: s, label: SUBJECT_NAMES[s] ?? s })),
    [courses]);
  // Quick-fill sets: the CS core courses of each year, taken from the data
  const yearSets = useMemo(() => {
    const core = courses.filter((c) => c.kind === "cs" && c.required_for_major);
    const sets = [1000, 2000].map((level) => ({
      label: `Year ${level / 1000} CS core`,
      codes: core.filter((c) => c.level === level).map((c) => c.code),
    }));
    sets.push({
      label: "Degree math and stats",
      codes: courses.filter((c) => c.kind === "support" && c.required_for_major).map((c) => c.code),
    });
    return sets;
  }, [courses]);

  function togglePreset(codes: string[]) {
    const allIn = codes.length > 0 && codes.every((c) => completed.includes(c));
    setCompleted(allIn ? completed.filter((c) => !codes.includes(c)) : [...new Set([...completed, ...codes])]);
  }

  const termOptions: Option[] = TERM_OPTIONS.map((t) => ({ value: t, label: t }));
  const interestOptions: Option[] = INTERESTS.map((i) => ({ value: i.id, label: i.label }));

  async function build() {
    setError("");
    setLoading(true);
    try {
      setResult(
        await api.plan({
          completed,
          terms: TERM_OPTIONS.filter((t) => terms.includes(t)),
          credit_target: creditTarget,
          strategy,
          include_core: core,
          extra_courses: extras,
          electives_per_term: electives,
          cs_electives_per_term: csElectives,
          elective_subjects: subjects,
          interest_areas: interests,
          accepted_into_major: accepted,
        })
      );
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="two-col">
      <section className="panel">
        <h2>Your situation</h2>
        <div className="field">
          <label>Quick fill</label>
          <div className="presets">
            {yearSets.map((y) => {
              const active = y.codes.length > 0 && y.codes.every((c) => completed.includes(c));
              return (
                <button key={y.label} type="button" className={active ? "preset active" : "preset"}
                  onClick={() => togglePreset(y.codes)}>
                  {active ? "✓ " : ""}{y.label} ({y.codes.length})
                </button>
              );
            })}
          </div>
          <div className="muted small">
            Ticks the required courses in that group, so you do not have to find them one by one. Untick any you have not
            finished below. If you took MATH 1006 or STAT 2550 instead of MATH 1000 or STAT 2500, tick those and untick the others.
          </div>
        </div>
        <CheckboxDropdown
          label="Courses you have completed"
          hint="Tick everything you have finished. Include MATH/STAT courses, which the planner cannot look up."
          options={completedOptions}
          values={completed}
          onChange={setCompleted}
          placeholder="Choose courses…"
          showChips
        />
        <CheckboxDropdown
          label="Extra CS courses you want (optional)"
          hint="Besides the core. The planner adds the prerequisites it can schedule."
          options={csOptions}
          values={extras}
          onChange={setExtras}
          placeholder="Choose courses…"
          showChips
        />
        <CheckboxDropdown
          label="Terms to plan"
          options={termOptions}
          values={terms}
          onChange={setTerms}
          placeholder="Choose terms…"
          searchable={false}
        />
        <div className="grid3">
          <div className="field">
            <label>Credit hours per term</label>
            <input type="number" min={3} max={21} value={creditTarget}
              onChange={(e) => setCreditTarget(Number(e.target.value) || 15)} />
          </div>
          <div className="field">
            <label>Strategy</label>
            <select value={strategy} onChange={(e) => setStrategy(e.target.value as Strategy)}>
              <option value="balanced">Balanced</option>
              <option value="lightest">Lightest workload</option>
              <option value="fastest">Fastest to finish</option>
            </select>
          </div>
        </div>
        <div className="grid3">
          <div className="field">
            <label>Other CS courses per term</label>
            <select value={csElectives} onChange={(e) => setCsElectives(Number(e.target.value))}>
              {[0, 1, 2, 3].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Non-CS electives per term</label>
            <select value={electives} onChange={(e) => setElectives(Number(e.target.value))}>
              {[0, 1, 2, 3].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
        </div>
        <p className="muted small">
          "Other CS courses" fills your term with eligible 3000/4000-level CS courses beyond the core.
          Electives are reserved first, so a high number can crowd out core courses.
        </p>
        <CheckboxDropdown
          label="CS areas you are interested in (optional)"
          options={interestOptions}
          values={interests}
          onChange={setInterests}
          placeholder="Any area"
          searchable={false}
        />
        {electives > 0 && (
          <CheckboxDropdown
            label="Elective subjects (optional)"
            hint="Leave empty for any subject, or tick some to only get electives from those."
            options={subjectOptions}
            values={subjects}
            onChange={setSubjects}
            placeholder="Any subject"
            searchable={false}
          />
        )}
        <label className="check"><input type="checkbox" checked={core} onChange={(e) => setCore(e.target.checked)} /> Include the courses the CS major requires (CS core, math and statistics)</label>
        <label className="check"><input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} /> I am accepted into the CS major</label>
        <button className="primary" onClick={build} disabled={loading || terms.length === 0}>
          {loading ? "Building…" : "Build my plan"}
        </button>
        {error && <div className="error">{error}</div>}
      </section>

      <section className="panel">
        <h2>Your plan</h2>
        {!result && <p className="muted">Fill in your courses and press Build my plan.</p>}
        {result && (
          <>
            {result.terms.map((t) => (
              <div key={t.term} className="term">
                <div className="term-head">
                  <strong>{t.term}</strong>
                  <span className="muted">{t.credit_hours} credit hours · about {t.est_hours_per_week} h/wk</span>
                </div>
                {t.courses.length === 0 && <p className="muted">Nothing eligible this term.</p>}
                {t.courses.map((c) => (
                  <div key={c.code} className="course-row">
                    <button className="link" onClick={() => onOpen(c.code)}>{c.code}</button> {c.title}
                    <span className={`role ${c.role}`}>{ROLE_LABELS[c.role]}</span>
                    <div className="muted small">
                      {c.credit_hours} CH · {c.load_hours} h/wk{c.load_source === "ratings" ? " (from ratings)" : c.load_source === "override" ? " (student-reported estimate)" : " (estimate)"}
                      {c.instructor ? ` · ${c.instructor}` : ""}
                      {c.ease != null ? ` · ease ${c.ease}/5` : ""}
                      {c.offering_unknown ? " · offering not confirmed" : ""}
                      {c.offering_assumed ? " · offering assumed" : ""}
                    </div>
                    {c.warnings.map((w) => <div key={w} className="warn small">{w}</div>)}
                  </div>
                ))}
                {t.warnings.map((w) => <div key={w} className="warn small">{w}</div>)}
              </div>
            ))}
            {result.unplaced.length > 0 && (
              <div className="term">
                <strong>Could not place</strong>
                {result.unplaced.map((u) => (
                  <div key={u.code} className="course-row">
                    <button className="link" onClick={() => onOpen(u.code)}>{u.code}</button> {u.title}
                    <div className="warn small">{u.reasons.join(" · ")}</div>
                  </div>
                ))}
              </div>
            )}
            {result.interest_blocked.length > 0 && (
              <div className="term">
                <strong>Courses in your interest areas that are not in the plan</strong>
                <div className="muted small">
                  Usually a missing MATH/STAT prerequisite. If you have finished one, tick it under completed courses and
                  build again.
                </div>
                {result.interest_blocked.map((b) => (
                  <div key={b.code} className="course-row">
                    <button className="link" onClick={() => onOpen(b.code)}>{b.code}</button> {b.title}
                    <div className="warn small">{b.reasons.join(" · ")}</div>
                  </div>
                ))}
              </div>
            )}
            {result.unknown_codes.length > 0 && (
              <div className="warn small">Not recognized: {result.unknown_codes.join(", ")}</div>
            )}
            <div className="term">
              <strong>Progress toward the CS major</strong>
              <div className="small">
                CS credit hours: {result.degree_progress.cs_hours.have} of {result.degree_progress.cs_hours.need}
                {" · "}3000/4000-level: {result.degree_progress.upper_hours.have} of {result.degree_progress.upper_hours.need}
                {" · "}4000-level: {result.degree_progress.fourk_hours.have} of {result.degree_progress.fourk_hours.need}
              </div>
              {result.degree_progress.required_missing.length > 0 ? (
                <div className="warn small">Required courses still not done or planned: {result.degree_progress.required_missing.join(", ")}</div>
              ) : (
                <div className="small">Every required course is done or planned.</div>
              )}
              <div className="muted small">{result.degree_progress.note}</div>
            </div>
            <div className="assumptions">
              <strong>Assumptions</strong>
              <ul>{result.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
