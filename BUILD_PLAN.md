# BUILD_PLAN.md — SplitWise Clone

---

## 1. Product Research

### How I studied Splitwise

I used Splitwise's web app and mobile app to map out every core workflow before writing a line of code. The research process:

1. **Signed up for Splitwise** and created test groups with dummy users to observe the full lifecycle: group creation → expense entry → balance computation → settlement.
2. **Traced data flows**: When you add an expense, what changes on the dashboard? What changes in the group view? What's the difference between "you owe" and "total group owes"?
3. **Identified the balance model**: Splitwise tracks net balances between user pairs, not per-expense. A simplification algorithm then collapses those pairs into minimum-payment suggestions.
4. **Studied split modes**: Opened the "Add expense" dialog and tested all four modes — equal, exact amounts, percentages, and shares — to understand the input model and validation rules.
5. **Observed real-time behaviour**: Messages on expenses update live without a page refresh.

### What I learned

- Splitwise's core data model is surprisingly simple: `User`, `Group`, `GroupMember`, `Expense`, `ExpenseSplit`, `Settlement`. Everything else is derived.
- The "simplified debts" view is a computed optimisation — the underlying data is always raw per-expense splits.
- Balances are always computed from splits + settlements, never stored as a separate table. This avoids sync issues.
- The chat feature is per-expense, not per-group. This shapes the data model (Message belongs to Expense, not Group).
- Settling up does not delete expenses — it creates a new `Settlement` record that offsets the balance.

### Workflows identified

| Workflow | Trigger | Outcome |
|---|---|---|
| Register | New user visits app | Account created, JWT issued, redirect to dashboard |
| Login | Returning user | JWT issued, redirect to dashboard |
| Create group | Click "New Group" on dashboard | Group + creator as admin added to GroupMember |
| Add member | Type email in group settings | User found, GroupMember record created |
| Remove member | Remove button in Members tab | GroupMember record deleted |
| Add expense | Click "+ Add Expense" in group | Expense + ExpenseSplit records created |
| Edit expense | Edit button on expense detail | Old splits deleted, new splits created |
| Delete expense | Delete button on expense detail | Expense + splits + messages cascade-deleted |
| View balances | Click Balances tab in group | Server computes net per member from expenses − settlements |
| Settle up | Click "Settle Up" button | Settlement record created, balances recomputed |
| Chat | Send message in expense detail | Socket.io broadcasts to all users in room |

### Product assumptions made

- One currency (INR) — no conversion needed
- Single payer per expense (one person paid the full bill)
- No expense categories
- No receipt image uploads
- No email verification on registration
- No friend list outside groups — social graph is derived entirely from group membership

---

## 2. Architecture

### Tech Stack Decision

| Layer | Choice | Why |
|---|---|---|
| Frontend | React 18 + Vite | Industry-standard, fast dev server, component model maps cleanly to the UI |
| Styling | TailwindCSS | Utility-first lets you build consistent UI fast without writing CSS |
| Routing | React Router v6 | Nested routes handle the Layout + pages pattern naturally |
| HTTP client | axios | Interceptors handle auth header injection globally — no per-request boilerplate |
| Backend | Node.js + Express | Minimal, fast to set up, large ecosystem |
| ORM | Prisma | Excellent DX, migrations, type safety, works with SQLite out of the box |
| Database | SQLite | Zero setup, file-based, fully relational — perfect for assignment/demo |
| Auth | JWT | Stateless, no session store needed |
| Real-time | Socket.io | Handles rooms, reconnection, and fallbacks automatically |

### Database Schema

Six models: `User`, `Group`, `GroupMember`, `Expense`, `ExpenseSplit`, `Settlement`, `Message`.

Key design decisions:
- `createdById` on Group stores the admin's userId (no separate FK to User) — simplifies admin checks
- `ExpenseSplit.amount` is always the computed INR value — the single source of truth for balance math
- `ExpenseSplit.percentage` and `ExpenseSplit.shares` are nullable metadata fields for display purposes only
- Cascade deletes: Group → members/expenses/settlements; Expense → splits/messages
- `@@unique([groupId, userId])` on GroupMember prevents duplicate membership

Full schema is in `backend/prisma/schema.prisma` and documented in `AI_CONTEXT.md` Section 5.

### API Design

REST API under `/api`. All protected routes use `Authorization: Bearer <token>`.

Design principles:
- Group-scoped resources use `/groups/:id/expenses` and `/groups/:id/settlements`
- Standalone expense operations use `/expenses/:id`
- Balance computation is a dedicated `GET /groups/:id/balances` endpoint — not embedded in the group response — because it's expensive to compute and not always needed
- Personal balance summary at `GET /users/me/balances` aggregates across all groups

Full API table in `README.md` and `AI_CONTEXT.md` Section 6.

### Frontend Structure

SPA with React Router v6. Two route groups:
- **Public routes** (`/login`, `/register`) — redirect to dashboard if already logged in
- **Private routes** (everything else) — redirect to login if not authenticated

Shared `Layout` component (dark sidebar + `<Outlet>`) wraps all private pages.

State management is intentionally simple:
- `AuthContext` holds user + token (global, persists to localStorage)
- All page-level data is fetched locally on mount
- No Redux or Zustand — unnecessary at this scale

### Deployment Approach

- **Backend**: Railway (supports persistent volumes for SQLite file, auto-detects Node.js)
- **Frontend**: Vercel (auto-detects Vite, CDN-deployed globally)
- CORS configured via `CLIENT_URL` env var — only the Vercel domain is whitelisted

---

## 3. AI Collaboration Process

### How I instructed the AI

I used Claude (claude.ai / Claude Code) as my primary engineering collaborator. My approach:

1. **Started with a scoping prompt** that gave Claude the full product requirements, tech stack decisions, DB schema, API routes, and UI page list — all decided upfront — and instructed it to build the complete project with no placeholders or TODOs.

2. **Backend first, then frontend** — I broke the work into a clear sequence so each layer could be reviewed before building the next.

3. **Explicit, complete specifications** — Instead of vague prompts like "build a login page", I provided the exact fields, behaviour, validation rules, and design tokens. This produced production-quality output on the first pass.

4. **Caught and fixed issues immediately** — When the PostgreSQL migration failed (missing credentials in DATABASE_URL), I pasted the exact error into the chat and Claude diagnosed it and provided a fix — then when I said I didn't want PostgreSQL at all, Claude switched the entire stack to SQLite in three file edits.

### What the AI was asked to do

- Generate the full Prisma schema
- Generate all Express routes, controllers, and middleware
- Generate all React pages and components
- Write balance computation logic from a plain-English spec
- Write split computation logic for all four modes
- Set up Socket.io rooms + JWT verification on message events
- Configure Tailwind, Vite, PostCSS
- Write all three documentation files

### How the plan evolved

| Iteration | What changed | Why |
|---|---|---|
| Initial build | PostgreSQL as database | Original plan assumed local Postgres |
| After migration error | Switched to SQLite | Postgres required server setup + credentials; SQLite is zero-config |
| After SQLite switch | Removed `mode: 'insensitive'` from user search | SQLite doesn't support this Prisma option |
| Documentation pass | Expanded AI_CONTEXT.md, BUILD_PLAN.md, added PROMPTS.md | Assignment requirement: docs must be detailed enough to recreate the app |

### How AI_CONTEXT.md was maintained

- Created in the initial build as a high-level architecture summary
- Expanded after each significant decision (database switch, API design choices)
- Final comprehensive version written to meet the assignment requirement: detailed enough that another developer or AI agent can recreate the app from it

---

## 4. Trade-offs

### What was simplified

| Feature | Simplification | Real Splitwise behaviour |
|---|---|---|
| Debt simplification | Show raw balances only | Splitwise computes minimum payments to settle all debts across a group |
| Multi-payer expenses | Single payer per expense | Splitwise allows splitting the "paid by" across multiple people |
| Balance caching | Computed on every request | Splitwise likely caches balances for performance |
| Notifications | None | Splitwise sends email + push on new expenses |
| Friend graph | Derived from group membership | Splitwise has a separate friends list independent of groups |

### What was hardcoded

- Currency: INR (₹) — the `currency` field exists in the DB for future extensibility but no UI is built for it
- JWT expiry: 7 days — no refresh token mechanism
- Avatar: initials-based with deterministic colour — no image upload

### What was avoided

- Session management (chose stateless JWT)
- Redis (no caching layer needed at this scale)
- Message queues (Socket.io is sufficient for real-time at demo scale)
- Unit/integration tests (manual testing checklist used instead)
- TypeScript (plain JS is faster to iterate with for a 2-day build)

### What I would improve with more time

1. **Debt simplification algorithm** — Implement the minimum-payment graph algorithm so users get "A pays B ₹200 to settle everything" instead of individual balances
2. **TypeScript** — Add types to the backend controllers and frontend API calls to catch bugs at compile time
3. **Pagination** — Add cursor-based pagination for expenses and messages
4. **PostgreSQL for production** — SQLite is fine for demos but PostgreSQL handles concurrent writes and is battle-tested for multi-user apps
5. **httpOnly cookies** — Replace localStorage JWT with httpOnly cookie to prevent XSS token theft
6. **Expense categories** — Tags/categories make filtering expenses much more useful
7. **Optimistic updates** — Chat messages could be shown immediately before the server confirms, improving perceived performance
8. **Smart debt suggestions** — "Settle with X" button that pre-fills the exact amount owed
