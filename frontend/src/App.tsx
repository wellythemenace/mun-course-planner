import { useState } from "react";
import CourseDrawer from "./components/CourseDrawer";
import CoursesTab from "./components/CoursesTab";
import ElectivesTab from "./components/ElectivesTab";
import PlanTab from "./components/PlanTab";
import ProfessorsTab from "./components/ProfessorsTab";
import type { OpenCourse } from "./types";

type Tab = "plan" | "electives" | "professors" | "courses";
const TABS: { id: Tab; label: string }[] = [
  { id: "plan", label: "Plan my semesters" },
  { id: "electives", label: "Find electives" },
  { id: "professors", label: "Professors" },
  { id: "courses", label: "All courses" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("plan");
  const [open, setOpen] = useState<{ code: string; rate: boolean; instructor?: string; term?: string } | null>(null);
  const onOpen: OpenCourse = (code, opts) =>
    setOpen({ code, rate: !!opts?.rate, instructor: opts?.instructor, term: opts?.term });

  return (
    <div className="app">
      <header className="topbar">
        <h1>MUN Course Planner</h1>
        <nav>
          {TABS.map((t) => (
            <button key={t.id} className={tab === t.id ? "tab active" : "tab"} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      <div className="banner">
        Built from MUN's 2026-27 calendar and the Computer Science department's tentative course list. An unofficial
        student project: always confirm with the official calendar and an academic advisor.
      </div>
      <main className="content">
        {tab === "plan" && <PlanTab onOpen={onOpen} />}
        {tab === "electives" && <ElectivesTab onOpen={onOpen} />}
        {tab === "professors" && <ProfessorsTab onOpen={onOpen} />}
        {tab === "courses" && <CoursesTab onOpen={onOpen} />}
      </main>
      {open && (
        <CourseDrawer
          key={`${open.code}|${open.rate}|${open.instructor ?? ""}`}
          code={open.code} rate={open.rate} instructor={open.instructor} term={open.term}
          onClose={() => setOpen(null)}
        />
      )}
    </div>
  );
}
