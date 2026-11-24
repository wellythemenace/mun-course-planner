// Links out to reviews written elsewhere. Nothing is copied into the app: these just open a search in a new tab.
const open = { target: "_blank", rel: "noopener noreferrer" } as const;

export function ProfessorReviewLink({ name }: { name: string }) {
  const q = encodeURIComponent(`${name} Memorial University RateMyProfessors`);
  return (
    <div className="small muted">
      Reviews elsewhere: <a className="ext" href={`https://www.google.com/search?q=${q}`} {...open}>Search RateMyProfessors ↗</a>
    </div>
  );
}

export function CourseReviewLink({ code }: { code: string }) {
  const q = encodeURIComponent(`Memorial University ${code}`);
  return (
    <div className="small muted">
      Reviews elsewhere: <a className="ext" href={`https://www.reddit.com/search/?q=${q}`} {...open}>Search Reddit ↗</a>
    </div>
  );
}
