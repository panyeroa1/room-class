# Tasks

Task ID: T-0001
Title: Rebrand README to Orbit
Status: DONE
Owner: Miles
Related repo or service: orbit-onyx
Branch: main
Created: 2026-01-17 23:22
Last updated: 2026-01-17 23:25

START LOG

Timestamp: 2026-01-17 23:22
Current behavior or state:

- README.md features "Onyx" branding, logo, and badges.

Plan and scope for this task:

- Rename "Onyx" to "Orbit" in README.md.
- Remove Onyx logos and badges.
- Ensure compliance with Eburon branding guidelines.

Files or modules expected to change:

- README.md

Risks or things to watch out for:

- Removing helpful links might make it harder for devs, but branding is priority.

WORK CHECKLIST

- [x] Code changes implemented according to the defined scope
- [x] No unrelated refactors or drive-by changes
- [x] Configuration and environment variables verified
- [x] Database migrations or scripts documented if they exist
- [x] Logs and error handling reviewed

END LOG

Timestamp: 2026-01-17 23:25
Summary of what actually changed:

- Replaced "Onyx" with "Orbit" in README.md.
- Removed Onyx logo, badges, and external links to onyx.app.
- Updated links to point to eburon.ai where appropriate.

Files actually modified:

- README.md

How it was tested:

- Manual verification of Markdown rendering via `view_file`.

Test result: PASS

Known limitations or follow-up tasks:

- "Onyx" references likely exist elsewhere in the codebase (e.g. package.json, backend code), but strictly followed scope for README.
