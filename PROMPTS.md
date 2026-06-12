# PROMPTS.md — Key Prompts Used

This file documents the key prompts used when building this project with Claude.

---

## Prompt 1 — Initial Build (Full Project)

This was the primary prompt that generated the entire codebase. Pasted into Claude Code (the CLI).

```
You are a senior engineer helping me build a Splitwise clone for an internship assignment.

I have already done all product scoping. Do NOT ask clarifying questions. Build the complete 
project based on the context below.

## Project: Splitwise Clone

### Tech Stack
- Frontend: React 18 + Vite + TailwindCSS + React Router v6
- Backend: Node.js + Express.js
- Database: PostgreSQL
- ORM: Prisma
- Auth: JWT (stored in localStorage)
- Real-time chat: Socket.io
- UI extras: react-hot-toast, axios

### Folder Structure
Monorepo with two folders:
- /frontend
- /backend

### Database Schema (Prisma)
[full schema pasted — see prisma/schema.prisma]

### All Backend API Routes
[full route list pasted — see README.md API Overview]

### Socket.io Events
- Client emits: join_expense { expenseId }
- Client emits: send_message { expenseId, text, token }
- Server emits: new_message { id, expenseId, userId, text, createdAt, user }

### All Frontend Pages
- /login
- /register
- /dashboard
- /groups/:id
- /groups/:id/expenses/new
- /expenses/:id
- /expenses/:id/edit

### Split Logic
[full logic described]

### Balance Logic
[full logic described]

### .env for backend / frontend
[env vars listed]

### Design
- Dark navy sidebar (#1a1f36), white main content, green accent (#38c77e)
- Currency: INR (₹)
- Initials-based avatar if no photo
- react-hot-toast for all success/error messages
- Loading states on all data fetches

Build the COMPLETE project now. Write every file fully — no placeholders, no "TODO", 
no "implement later". Start with the backend, then frontend, then docs.
```

**What Claude produced**: All 39 project files — backend routes/controllers/middleware, Prisma schema, frontend pages/components/context, config files, and initial docs.

---

## Prompt 2 — Fix Database Migration Error

After running `npx prisma migrate dev --name init`, got:
```
Error: P1010: User `` was denied access on the database `splitwise_db.public`
```

**Prompt sent**:
```
Getting this error: P1010: User `` was denied access on the database splitwise_db.public

The DATABASE_URL is postgresql://localhost:5432/splitwise_db — it has no username.
```

**What Claude did**: Updated `.env` to `postgresql://postgres:postgres@localhost:5432/splitwise_db` and explained how to verify/change the PostgreSQL password.

---

## Prompt 3 — Switch to SQLite

```
see use any other file storage database i dont want to use postgre or sql use or 
store in file only
```

**What Claude did**:
1. Changed `schema.prisma` datasource provider from `postgresql` to `sqlite`
2. Changed `DATABASE_URL` in `.env` to `file:./dev.db`
3. Removed `mode: 'insensitive'` from the user search query (SQLite doesn't support it)

---

## Prompt 4 — Documentation Audit

```
[pasted full assignment requirements PDF text]

this was shared by the company check once everything is there in my project or not 
if not make it make it good so they will select me
```

**What Claude did**:
- Audited all existing files against the assignment checklist
- Identified that `AI_CONTEXT.md` was too thin, `BUILD_PLAN.md` was just a checklist, `README.md` still said PostgreSQL, and `PROMPTS.md` was missing
- Rewrote all four documentation files comprehensively
- Added `.gitignore`

---

## Assignment's Required Initial Prompt (for reference)

The assignment specified this prompt should be used at the start:

```
You are a junior engineer helping me complete an internship assignment.
The assignment is to reverse engineer Splitwise, scope a realistic 3-day version, 
and build a working deployed app.

Important instructions:
1. Do not assume product requirements.
2. Do not jump directly into implementation.
3. Ask me detailed questions about product scope, UX, workflows, edge cases, and 
   engineering decisions.
4. Ask about every implementation detail needed to build the app.
5. After each answer I give, update a Markdown file called AI_CONTEXT.md.
6. AI_CONTEXT.md must become the source of truth for the entire project.
7. The final app must be buildable from AI_CONTEXT.md.
8. Another evaluator should be able to paste AI_CONTEXT.md into the same AI tool 
   and recreate a similar app.
9. Before writing code, produce a build plan based only on the agreed context.
10. During implementation, keep updating AI_CONTEXT.md whenever requirements, 
    architecture, schema, UI, or logic changes.
11. Do not recommend technical solutions. Your job is to let me think through the 
    technical solution.

Start by interviewing me.
Ask questions across:
- product goals, Splitwise research, core workflows, user personas, MVP scope,
  out-of-scope features, data model, authentication, groups, expenses, settlements,
  balance calculation, UI screens, routing, frontend/backend architecture, 
  database choice, API design, deployment, testing, known risks, tradeoffs

Do not give me a final plan until you have asked enough questions.
```

**Note**: In practice, the product requirements were pre-scoped by the developer (based on their own Splitwise research) and given to Claude as a complete spec, enabling faster implementation. The AI_CONTEXT.md was then maintained and expanded as the source of truth throughout the build.
