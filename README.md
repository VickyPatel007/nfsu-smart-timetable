# NFSU Smart Timetable

Constraint-aware academic timetabling for the **School of Cyber Security & Digital Forensics, National Forensic Sciences University**. It plans theory lectures and batch-wise lab practicals across programmes, faculty and specialised labs with no double-booking, then lets the timetable office review, lock, print and publish the week.

## What's here

- **Overview**: the week at a glance. Headline figures, today's sessions, constraint health, faculty load and room occupancy.
- **Timetable**: an interactive week grid for any section, faculty member or room, with session details, clash-free alternatives, locking, print and CSV export.
- **Faculty** and **Rooms & Labs** directories with weekly occupancy maps.

The app currently runs on a realistic demo dataset (`src/data/fixtures.ts`) covering all five SCSDF programmes: B.Tech–M.Tech CSE (CS), M.Tech CS, M.Tech AI & DS, M.Sc. CS and M.Sc. DFIS.

## Tech

- [TanStack Start](https://tanstack.com/start) (React 19, file-based routing, SSR)
- Tailwind CSS 4
- TanStack Store for client UI state
- Deployed on Netlify

The original Python/Flask implementation (scheduler, validator, templates) lives in `legacy/smart-timetable-flask/` for reference while the engine is ported.

## Run locally

```bash
pnpm install
netlify dev        # or: pnpm dev
```

## Run with Docker

Docker provides a consistent local demo environment without installing Node.js
on the host machine:

```bash
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000). Stop it with:

```bash
docker compose down
```

Netlify Identity login and signup require a real Netlify deployment and do not
authenticate on localhost, including inside Docker. Use a Netlify branch
preview to test `/login`, `/admin`, and `/student` authentication.

For the local Docker demo, use `admin` / `admin` for the admin panel or
`student` / `student` for the student panel. Local student signup is also
enabled in development mode.

## Roadmap

See [PLAN.md](./PLAN.md). Next up: the data model on Netlify Database, then management screens, the TypeScript scheduling engine, drag-to-edit with instant clash checks, role-based accounts, and sharing/export.
