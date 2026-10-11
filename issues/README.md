# issues/

Detailed specifications for substantial tasks: work that spans multiple repositories or needs a durable implementation brief. Small single-repo tasks can live in that repository's own tracker; anything an agent needs lasting context for belongs here.

## Convention

- One Markdown file per issue, named `NNN-short-slug.md` (e.g., `001-versioned-api-contract.md`).
- Each issue uses [../templates/task-template.md](../templates/task-template.md): objective and problem statement, evidence and current behavior, scope and non-goals, affected repositories, dependencies and risks, proposed approach, acceptance criteria, test plan, documentation updates.
- Link the issue from the relevant [../ROADMAP.md](../ROADMAP.md) item; do not duplicate the roadmap here.
- Status lives at the top of the file (open / in progress / blocked / done) with a date on each change.

No issues filed yet. Candidates from the audit's P0 list: Docker/secret handling, auth error statuses and server-side authorization, database backup and restore drill.
