# AGENTS.md

NFSU Smart Timetable: an academic timetable generator for NFSU's School of Cyber Security & Digital Forensics, built with TanStack Start on Netlify. **Read `PLAN.md` first.** It's the roadmap, and new work should continue from the next unchecked milestone.

## Stack

TanStack Start (React 19, TanStack Router file routes, Vite 7), Tailwind CSS 4 (theme tokens in `src/styles.css`), TanStack Store, lucide-react icons. TypeScript strict.

## Layout

```
src/
  data/
    types.ts        # Domain types (mirror the original Flask data model field-for-field, snake_case)
    fixtures.ts     # Demo dataset. Single source of data until Netlify Database lands (PLAN milestone 2)
  lib/
    timetable.ts    # Pure helpers: time slots, lookups, session→Block merging, load/utilisation, CSV, subject colours
    insights.ts     # Overview metrics + soft-constraint scores
    store.ts        # Client-only UI state (locks, publish status, generate dialog)
    useToday.ts     # Client-resolved date to avoid SSR hydration mismatch
  components/
    AppShell.tsx    # Sidebar/mobile nav, wraps every page (used in __root.tsx)
    WeekGrid.tsx    # CSS-grid week view; practical blocks span consecutive period rows
    SessionDrawer.tsx, GenerateDialog.tsx, MiniWeek.tsx, ui.tsx (primitives)
  routes/           # index (Overview), timetable, faculty, rooms
legacy/smart-timetable-flask/  # Original Python app: reference for porting scheduler.py / validator.py. Not built or deployed.
```

## Conventions & decisions

- Data shape stays identical to the legacy JSON (snake_case) so the Python scheduler logic ports 1:1.
- A "Block" is one or more `ScheduledSession`s merged (consecutive practical periods for the same subject/batch/room). Locks apply to every session id in a block.
- `/timetable` search params: `view` (`section|faculty|room`) and `id`, both optional; defaults to the first entity.
- Visual language: ivory paper (`paper`), ink text, oxblood accent, gold highlights, sage = labs/success, ochre = fixed/draft. Serif (Fraunces) for headings and numerals, mono for codes and times. Subject colours come from `subjectColor()`.
- Anything date/time-dependent renders on the client via `useToday()`.
- Classes `no-print` / `print-only` control the printable timetable.
- The Generate dialog only animates over the fixtures right now; the real engine is PLAN milestone 4.
