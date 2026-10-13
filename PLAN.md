# NFSU Smart Timetable — Product Roadmap

The product is being rebuilt as a Netlify-native web app (TanStack Start + React) in stages. Each milestone below is self-contained and ships something usable.

## ✅ Milestone 1 — Product surface (done)

- New light, academic visual identity (Fraunces / Instrument Sans / JetBrains Mono on an ivory "paper" palette).
- **Overview** (`/`): headline figures, today's sessions timeline, constraint health (10 hard rules + 3 soft scores computed from the data), faculty load, room occupancy heatmap, programme cards.
- **Timetable** (`/timetable`): week grid for any section, faculty member or room; colour per subject; 2-hour lab blocks; session drawer with a live constraint check, clash-free alternative slots, and lock toggle; subject focus; print layout; CSV export; publish/unpublish.
- **Faculty** (`/faculty`) and **Rooms & Labs** (`/rooms`) directories with weekly occupancy maps, load/utilisation meters and a live "in use / free now" indicator.
- Generate dialog that walks through the engine's stages.
- All data comes from `src/data/fixtures.ts`; lock/publish state is client-only (`src/lib/store.ts`).

## Milestone 2 — Data model on Netlify Database

- Drizzle schema in `db/schema.ts`: settings, rooms, programmes → semesters → sections → batches, faculty (+ availability/preferences), subjects, fixed sessions, scheduled sessions, generation runs.
- Seed script that loads the current fixtures.
- Replace fixture imports with TanStack Start server functions / loaders; keep `src/lib/timetable.ts` helpers working on loaded data.

## Milestone 3 — Management screens

- CRUD screens for Programmes/Sections/Batches, Subjects, Faculty (availability and preference editor on a week grid), Rooms, and University settings (hours, breaks, period length).
- Server-side validation (zod) mirroring `legacy/smart-timetable-flask/security.py` (time regex, day whitelist, length and range limits).

## Milestone 4 — Scheduling engine in TypeScript

- Port `legacy/smart-timetable-flask/scheduler.py` and `validator.py` to TypeScript, running in a Netlify Function (background function for large inputs).
- Persist each run with its result: placed sessions, unscheduled tasks, and a plain-language bottleneck explanation ("Dr. Khan is over capacity on Friday").
- Fix carried over from the original: practicals must be stored as consecutive multi-period blocks (the old `data.json` stored them as single hours).
- Port `test_acceptance.py` as automated tests for the engine.

## Milestone 5 — Interactive editing & conflicts

- Drag a session to another slot; validate instantly (port of `validate_single_edit`) and reject clashes with a reason.
- Persist locks; "Conflicts" screen listing violations with one-click jumps to the cell.

## Milestone 6 — Accounts & roles (Netlify Identity)

- Initial role gateway and authenticated portals are now implemented: `/login`, `/admin`, and `/student`.
- Admin publication status is persisted in Netlify Blobs and protected by a server-side admin role check.
- Timetable office (admin): full control, publish.
- Faculty: view own week, submit availability/leave.
- Students: read-only access to the published timetable for their section.

## Milestone 7 — Sharing & export

- PDF export with university header, per-section/faculty iCal feeds, shareable read-only links for published timetables.

## Milestone 8 — Hardening

- Security headers (CSP, frame-ancestors, referrer policy) in `netlify.toml`; drop the deprecated `X-XSS-Protection`.
- Platform-level rate limiting in place of the in-memory limiter, which doesn't work across serverless instances.
