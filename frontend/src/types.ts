export interface RatingSummary {
  count: number;
  enough: boolean;
  min_needed: number;
  avg_ease?: number;
  avg_workload_hours?: number | null;
  exam_types?: Record<string, number>;
  readings?: Record<string, number>;
  marking?: Record<string, number>;
}

export interface CourseSummary {
  code: string;
  title: string;
  credit_hours: number;
  kind: "cs" | "elective" | "support";
  subject: string;
  level: number;
  prereq_text: string;
  offered_terms: string[];
  needs_review: string | null;
  required_for_major: boolean;
  rating: RatingSummary;
}

export interface Offering {
  term: string;
  instructor: string | null;
  department: string | null;
}

export interface CourseComment {
  ease: number;
  term: string | null;
  instructor: string | null;
  comment: string;
  source: string;
  created_at: string;
}

export interface CourseDetail extends CourseSummary {
  coreq: string[];
  requires_program_acceptance: string | null;
  note: string | null;
  required_for_major: boolean;
  concentration: string | null;
  offerings: Offering[];
  recent_comments: CourseComment[];
}

export interface ProfessorOffering {
  term: string;
  course_code: string;
  title: string;
}

export interface Professor {
  id: number;
  name: string;
  department: string | null;
  offerings: ProfessorOffering[];
  rating: RatingSummary;
}

export type Strategy = "lightest" | "balanced" | "fastest";

export interface PlanRequest {
  completed: string[];
  terms: string[];
  credit_target: number;
  strategy: Strategy;
  include_core: boolean;
  extra_courses: string[];
  electives_per_term: number;
  cs_electives_per_term: number;
  elective_subjects: string[];
  interest_areas: string[];
  accepted_into_major: boolean;
}

export interface PlanCourse {
  code: string;
  title: string;
  credit_hours: number;
  kind: "cs" | "elective" | "support";
  role: "core" | "chosen" | "cs_elective" | "elective" | "prereq";
  load_hours: number;
  load_source: "ratings" | "default" | "override";
  ease: number | null;
  offering_assumed: boolean;
  offering_unknown: boolean;
  instructor: string | null;
  warnings: string[];
}

export interface PlanTerm {
  term: string;
  courses: PlanCourse[];
  credit_hours: number;
  est_hours_per_week: number;
  warnings: string[];
}

export interface PlanResult {
  terms: PlanTerm[];
  unplaced: { code: string; title: string; reasons: string[] }[];
  interest_blocked: { code: string; title: string; area: string; reasons: string[] }[];
  degree_progress: {
    cs_hours: { have: number; need: number };
    upper_hours: { have: number; need: number };
    fourk_hours: { have: number; need: number };
    required_missing: string[];
    note: string;
  };
  unknown_codes: string[];
  assumptions: string[];
}

export interface RatingInput {
  course_code: string;
  ease: number;
  instructor?: string;
  term?: string;
  workload_hours?: number;
  assessments?: number;
  exam_type?: "none" | "take_home" | "in_person" | "mixed";
  readings?: "light" | "medium" | "heavy";
  marking?: "lenient" | "fair" | "harsh";
  comment?: string;
}

// Opening a course: `rate` jumps to the rating form, `instructor` and `term` pre-fill it.
export type OpenOpts = { rate?: boolean; instructor?: string; term?: string };
export type OpenCourse = (code: string, opts?: OpenOpts) => void;
