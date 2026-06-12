# AI_CONTEXT.md — SplitWise Clone

> This file is the single source of truth for the entire project.
> It was created and maintained throughout the build process with Claude (claude.ai).
> Another developer or AI agent should be able to paste this file into Claude and recreate a near-identical app.

---

## 1. Product Understanding

### What is Splitwise?
Splitwise is an expense-splitting application that helps groups of people track shared expenses and settle debts. Core behaviour:
- Users form groups (trips, households, couples, etc.)
- Any group member can log an expense and choose how to split it
- Splitwise tracks who paid and who owes whom, computing running net balances
- When someone pays another person back, they record a settlement which reduces the debt
- The app shows a simplified "who owes who" view, not every individual transaction

### Core workflows identified from studying Splitwise
1. **Register/Login** → land on dashboard
2. **Dashboard** → see all groups + personal "you owe / you are owed" summary
3. **Create group** → name it, search for friends by email, add them
4. **Add expense** → pick group, enter amount, description, who paid, how to split
5. **View group** → see expense list, current balances per member
6. **Settle up** → record that person A paid person B a cash amount
7. **Expense detail** → see each person's share, comment thread

### User personas
- **Primary**: Friend groups splitting bills (meals, trips, rent)
- **Secondary**: Roommates tracking ongoing household expenses

---

## 2. Product Scope (MVP)

### In scope
- Email/password auth with JWT
- Create and manage groups (invite by email, remove members)
- Add expenses with 4 split modes: equal, unequal, percentage, shares
- Group-level balance per member (who owes whom within a group)
- Personal balance summary across all groups (dashboard)
- Record settlements (reduce debt between two users)
- Real-time chat thread per expense (Socket.io)
- Edit and delete expenses
- Delete groups (admin only)

### Out of scope (explicitly excluded)
- Social login (Google/GitHub OAuth)
- Email notifications / push notifications
- Smart debt simplification (Splitwise's "simplify debts" algorithm)
- Multi-currency with live exchange rates
- Recurring expenses
- Expense categories / tags / receipts
- Mobile app
- Friend relationships outside of groups
- Export to CSV/PDF
- Avatar image upload

---

## 3. Engineering Requirements

### General
- Monorepo with `/backend` and `/frontend` folders
- Backend serves JSON API only (no SSR)
- Frontend is a pure SPA (React)
- All amounts stored as floating-point numbers (Float in Prisma → REAL in SQLite)
- Currency hardcoded to INR (₹) with currency field in DB for future extensibility
- Timestamps stored as ISO 8601 UTC

### Auth
- Passwords hashed with bcryptjs (salt rounds: 10)
- JWT signed with HS256, expires in 7 days
- Token stored in localStorage (acceptable for assignment; production would use httpOnly cookies)
- Axios interceptor attaches `Authorization: Bearer <token>` to every request
- 401 response from any endpoint → clear storage, redirect to /login

### Groups
- Creator is automatically added as admin, all other members added as "member"
- Any member can add expenses; only creator (admin) can delete the group
- Members are searched by partial email match

### Expenses
- Created inside a group context
- `paidById` is the single person who paid upfront
- `splitType` controls how amounts are divided among `memberIds`
- All four split types ultimately store a computed `amount` in `ExpenseSplit` — this is the definitive value used in all balance calculations
- Deleting an expense cascades to splits and messages

### Split logic (server-side, `expenseController.js`)
```
equal:
  each member's amount = total / n

unequal:
  each member's amount = splitData[userId]
  validation: sum(splitData values) must equal total (±0.01 tolerance, enforced client-side)

percentage:
  each member's amount = (splitData[userId] / 100) * total
  stored: amount + percentage field
  validation: sum(percentages) must equal 100 (±0.01, client-side)

shares:
  totalShares = sum(splitData values)
  each member's amount = (splitData[userId] / totalShares) * total
  stored: amount + shares field
```

### Balance logic (server-side, `groupController.js`)
```
For each expense in a group:
  paidBy user GAINS credit for: each other member's split amount
  each other member OWES: their own split amount to paidBy

For each settlement:
  fromUser's debt to toUser is reduced by settlement.amount
  toUser's credit from fromUser is reduced by settlement.amount

Net per user = totalOwed (others owe them) − totalOwes (they owe others)
Positive net = they are owed money
Negative net = they owe money
```

### Real-time chat
- Socket.io rooms named `expense:{expenseId}`
- Client emits `join_expense` on page load
- Client emits `send_message` with `{ expenseId, text, token }` — token is included because Socket.io has no session
- Server verifies JWT on each message, creates DB record, broadcasts `new_message` to room
- Message history fetched via REST on page load; Socket.io only handles new messages

---

## 4. Tech Stack

| Concern | Choice | Reason |
|---|---|---|
| Frontend framework | React 18 | Industry standard, component model suits this UI |
| Build tool | Vite | Fast HMR, minimal config |
| Styling | TailwindCSS | Rapid utility-first styling |
| Routing | React Router v6 | Nested routes, loader pattern |
| HTTP client | axios | Interceptors for auth header injection |
| Toasts | react-hot-toast | Minimal, beautiful |
| Backend runtime | Node.js + Express | Simple, vast ecosystem |
| ORM | Prisma | Type-safe, excellent migrations, works with SQLite |
| Database | SQLite (file: ./prisma/dev.db) | Zero-config, no server required, relational |
| Auth | JWT (jsonwebtoken) | Stateless, easy to implement |
| Password hashing | bcryptjs | Battle-tested |
| Real-time | Socket.io | Handles rooms and reconnection gracefully |

---

## 5. Database Schema

```prisma
model User {
  id           String   @id @default(uuid())
  email        String   @unique
  name         String
  passwordHash String
  avatar       String?
  createdAt    DateTime @default(now())

  groupMembers    GroupMember[]
  expensesPaid    Expense[]       @relation("PaidBy")
  splits          ExpenseSplit[]
  messagesSent    Message[]
  settlementsFrom Settlement[]    @relation("FromUser")
  settlementsTo   Settlement[]    @relation("ToUser")
}

model Group {
  id          String   @id @default(uuid())
  name        String
  description String?
  createdById String   -- userId of admin/creator (not a FK, just stored)
  createdAt   DateTime @default(now())

  members     GroupMember[]
  expenses    Expense[]
  settlements Settlement[]
}

model GroupMember {
  id       String   @id @default(uuid())
  groupId  String
  userId   String
  role     String   @default("member")   -- "admin" | "member"
  joinedAt DateTime @default(now())

  group Group @relation(...)
  user  User  @relation(...)
  @@unique([groupId, userId])
}

model Expense {
  id          String   @id @default(uuid())
  groupId     String
  description String
  amount      Float
  currency    String   @default("INR")
  paidById    String
  splitType   String   -- "equal" | "unequal" | "percentage" | "shares"
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt

  group    Group          @relation(...)
  paidBy   User           @relation("PaidBy", ...)
  splits   ExpenseSplit[]
  messages Message[]
}

model ExpenseSplit {
  id         String  @id @default(uuid())
  expenseId  String
  userId     String
  amount     Float    -- always the computed INR amount (definitive)
  percentage Float?   -- only set for "percentage" split
  shares     Int?     -- only set for "shares" split

  expense Expense @relation(...)
  user    User    @relation(...)
  @@unique([expenseId, userId])
}

model Settlement {
  id         String   @id @default(uuid())
  groupId    String
  fromUserId String   -- person who paid
  toUserId   String   -- person who received
  amount     Float
  note       String?
  createdAt  DateTime @default(now())

  group    Group @relation(...)
  fromUser User  @relation("FromUser", ...)
  toUser   User  @relation("ToUser", ...)
}

model Message {
  id        String   @id @default(uuid())
  expenseId String
  userId    String
  text      String
  createdAt DateTime @default(now())

  expense Expense @relation(...)
  user    User    @relation(...)
}
```

All cascading deletes:
- Group deleted → GroupMember, Expense, Settlement deleted
- Expense deleted → ExpenseSplit, Message deleted

---

## 6. API Design

All routes prefixed with `/api`. All protected routes require `Authorization: Bearer <token>`.

### Auth
```
POST /api/auth/register    body: { email, name, password }
POST /api/auth/login       body: { email, password }
GET  /api/auth/me          protected → returns current user
```

### Users
```
GET /api/users/search?email=   protected → fuzzy email search, excludes self
GET /api/users/me/balances     protected → net balance with every other user across all groups
```

### Groups
```
GET    /api/groups                      protected → all groups where current user is member
POST   /api/groups                      body: { name, description?, memberIds[] }
GET    /api/groups/:id                  protected → group + members + expenses with splits
PUT    /api/groups/:id                  body: { name?, description? } — admin only
DELETE /api/groups/:id                  admin only, cascades everything
POST   /api/groups/:id/members          body: { userId }
DELETE /api/groups/:id/members/:userId
GET    /api/groups/:id/balances         computed balance per member
GET    /api/groups/:id/expenses         all expenses with paidBy + splits
POST   /api/groups/:id/expenses         body: { description, amount, paidById, splitType, memberIds[], splitData{} }
GET    /api/groups/:id/settlements
POST   /api/groups/:id/settlements      body: { fromUserId, toUserId, amount, note? }
```

### Expenses
```
GET    /api/expenses/:id    expense + splits + group info
PUT    /api/expenses/:id    same body as create, replaces splits
DELETE /api/expenses/:id    cascades splits + messages
GET    /api/expenses/:id/messages   ordered asc by createdAt
```

### Socket.io
```
Client emits:  join_expense   { expenseId }
Client emits:  send_message   { expenseId, text, token }
Server emits:  new_message    { id, expenseId, userId, text, createdAt, user: { id, name, avatar } }
Server emits:  error          { message }  (if token invalid)
```

---

## 7. Frontend Structure

### Routing (`App.jsx`)
```
/login          → Login.jsx         (public only)
/register       → Register.jsx      (public only)
/               → redirect to /dashboard
/dashboard      → Dashboard.jsx     (private)
/groups/:id     → GroupPage.jsx     (private)
/groups/:id/expenses/new  → NewExpense.jsx  (private)
/expenses/:id   → ExpenseDetail.jsx  (private)
/expenses/:id/edit → EditExpense.jsx (private)
```

Route guards: `PrivateRoute` redirects unauthenticated users to `/login`. `PublicRoute` redirects authenticated users to `/dashboard`.

### State management
- Global auth state in `AuthContext` (React Context + useState)
- All other state is local to each page component (no Redux/Zustand needed at this scale)
- Data fetched on mount with `useEffect` + `api.get()`

### Key components

| Component | Purpose |
|---|---|
| `Layout.jsx` | Dark sidebar with nav + user info + logout. Main content area as `<Outlet />` |
| `Avatar.jsx` | Deterministic colour from name charcode. Falls back to initials if no image. |
| `CreateGroupModal.jsx` | Form with live user search by email, multi-member selection |
| `SettleModal.jsx` | Dropdown from/to from group members, amount + optional note |

### Page summaries

**Dashboard** — Three stat cards (total groups, total owed, total owes). Group list with member avatars. Personal balance list.

**GroupPage** — Four tabs: Expenses (linked list), Balances (per-member net), Settlements (history), Members (role badges). My balance banner at top.

**NewExpense / EditExpense** — Description, amount, paid-by dropdown, split type toggle (4 options), member checklist. When split ≠ equal, per-member numeric input appears inline. Client-side validation before submit.

**ExpenseDetail** — Left panel: amount, paid-by, per-member splits. Right panel: full-height chat with real-time Socket.io updates.

### Design system
- Sidebar colour: `#1a1f36` (dark navy)
- Accent colour: `#38c77e` (green) — buttons, active states, positive balances
- Background: `#f8f9ff` (off-white)
- Cards: white with `border-gray-100` and `shadow-sm`
- Border radius: `rounded-xl` (12px) for inputs, `rounded-2xl` (16px) for cards

---

## 8. Deployment Plan

### Backend → Railway
- Connect GitHub repo, set root directory to `/backend`
- Add a Railway volume at `/app/prisma` to persist `dev.db`
- Start command: `npx prisma migrate deploy && node src/index.js`
- Environment variables: `DATABASE_URL`, `JWT_SECRET`, `CLIENT_URL` (Vercel URL), `PORT`

### Frontend → Vercel
- Connect GitHub repo, set root directory to `/frontend`
- Vite build auto-detected
- Environment variables: `VITE_API_URL`, `VITE_SOCKET_URL` (Railway URL)

### CORS
`CLIENT_URL` env var is the only allowed origin in Express cors config.

---

## 9. Testing Plan

Manual testing checklist:
- [ ] Register two separate user accounts (A and B)
- [ ] User A creates a group, adds user B by email
- [ ] User A adds an equal-split expense → verify each person owes half
- [ ] User A adds a percentage-split expense → verify % validation and amounts
- [ ] User A adds an unequal expense → verify sum validation
- [ ] User A adds a shares expense → verify proportional amounts
- [ ] Check group balances tab reflects correct debts
- [ ] Check dashboard personal balance summary
- [ ] User B opens expense detail, sends a chat message → User A sees it live (real-time)
- [ ] Record a settlement from B to A → verify balance reduces
- [ ] Edit an expense → verify splits recalculated
- [ ] Delete an expense → verify removed from list and balances updated
- [ ] Log out and log back in → JWT persists session
- [ ] Invalid token (clear localStorage manually) → redirects to /login

---

## 10. Changes Made During Implementation

| # | Change | Reason |
|---|---|---|
| 1 | Switched database from PostgreSQL to SQLite | PostgreSQL requires a running server + credentials; SQLite is zero-config and file-based, removing the setup barrier entirely. Prisma makes this a one-line change in `schema.prisma`. |
| 2 | Removed `mode: 'insensitive'` from user search query | SQLite does not support Prisma's `mode: 'insensitive'` filter (it's PostgreSQL-only). Removed it; SQLite's LIKE is case-insensitive by default for ASCII. |
| 3 | DATABASE_URL changed to `file:./dev.db` | Required format for Prisma SQLite provider |

---

## 11. Trade-offs

| Decision | What was simplified | Impact |
|---|---|---|
| SQLite over PostgreSQL | No concurrent write support, no connection pooling | Fine for demo and single-server deployment; would need PostgreSQL for production scale |
| JWT in localStorage | Vulnerable to XSS (vs httpOnly cookie) | Acceptable for internship assignment; noted as known limitation |
| No debt simplification | Splitwise shows optimised "pay X to settle everyone" — we just show raw balances | Users must manually figure out optimal payment order |
| No avatar upload | Initials-based deterministic colour avatar | No file storage dependency |
| No email verification | Users can register with any email | Simplifies auth flow; fine for demo |
| Balance computed on-the-fly | No cached balance table | Slightly slower on large datasets but always accurate; no sync bugs |
| Single paidBy per expense | Splitwise allows split payments (multiple payers) | Covered 95% of real-world use cases |
| Float for amounts | Floating-point arithmetic has rounding issues | For a demo app with INR amounts this is acceptable; production should use integer paise |

---

## 12. Known Limitations

- SQLite has no concurrent write support — acceptable for single-server demo
- Float arithmetic can cause ₹0.01 rounding differences in split totals
- No automatic debt simplification across multiple expenses
- No pagination — all expenses/messages loaded at once
- No rate limiting on API endpoints
- JWT not revocable (no token blacklist) — logout only clears client-side storage
- Socket.io falls back to long-polling if WebSocket is blocked; messages may have slight delay
- SQLite data is lost if the server restarts without a persistent volume (Railway volume solves this)

---

## 13. Key Prompts Used

See `PROMPTS.md` for the complete prompt log.

---

## 14. Rebuilding This App

To recreate this app from scratch using this context file:

1. Create `/backend` with Express + Prisma, using the exact schema in Section 5
2. Implement each controller following the logic in Section 3 and the API spec in Section 6
3. Wire Socket.io as described in Section 3 (Real-time chat)
4. Create `/frontend` with Vite + React + TailwindCSS
5. Implement routes as specified in Section 7
6. Implement each page and component following the descriptions in Section 7
7. Apply the design system from Section 7 (colours, spacing)
8. Test against the checklist in Section 9
9. Deploy per Section 8
