# SplitWise Clone

A full-stack expense-splitting application inspired by Splitwise, built as an internship assignment.

**AI Tool Used**: Claude (claude.ai / Claude Code) — used as the primary development collaborator throughout the entire build.

---

## Live Demo

> Deploy the app using the instructions below. A Railway + Vercel deployment is recommended (see [Deployment](#deployment)).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + TailwindCSS + React Router v6 |
| Backend | Node.js + Express.js |
| Database | SQLite (file-based, via Prisma ORM) |
| Auth | JWT stored in localStorage |
| Real-time | Socket.io |
| UI Helpers | react-hot-toast, axios |

---

## Features

- **Authentication** — Register and login with email/password. JWT persists across page refreshes.
- **Groups** — Create groups, search and add members by email, remove members.
- **Expenses** — Add expenses with four split modes:
  - **Equal** — divided evenly across all selected members
  - **Unequal** — each member's amount entered manually (validated to sum to total)
  - **Percentage** — each member gets a % (validated to sum to 100)
  - **Shares** — integer share counts, amounts computed proportionally
- **Balances** — Group-level balance breakdown per member and personal balance summary across all groups.
- **Settlements** — Record cash payments between any two members to reduce outstanding debts.
- **Real-time Chat** — Each expense has a live discussion thread powered by Socket.io.

---

## Project Structure

```
project/
├── README.md
├── BUILD_PLAN.md
├── AI_CONTEXT.md
├── PROMPTS.md
├── backend/
│   ├── .env
│   ├── package.json
│   ├── prisma/
│   │   └── schema.prisma          # Full DB schema
│   └── src/
│       ├── index.js               # Express + Socket.io entry
│       ├── middleware/
│       │   └── auth.js            # JWT verification middleware
│       ├── routes/                # Route definitions
│       │   ├── auth.js
│       │   ├── users.js
│       │   ├── groups.js
│       │   ├── expenses.js
│       │   ├── settlements.js
│       │   └── messages.js
│       └── controllers/           # Business logic
│           ├── authController.js
│           ├── groupController.js
│           ├── expenseController.js
│           ├── settlementController.js
│           ├── userController.js
│           └── messageController.js
└── frontend/
    ├── .env
    ├── index.html
    ├── vite.config.js
    ├── tailwind.config.js
    └── src/
        ├── main.jsx
        ├── App.jsx                # Routes + auth guards
        ├── index.css
        ├── api/
        │   └── axios.js           # Axios instance with auth interceptor
        ├── context/
        │   └── AuthContext.jsx    # Global auth state
        ├── components/
        │   ├── Layout.jsx         # Sidebar + outlet
        │   ├── Avatar.jsx         # Initials-based colored avatar
        │   ├── CreateGroupModal.jsx
        │   └── SettleModal.jsx
        └── pages/
            ├── Login.jsx
            ├── Register.jsx
            ├── Dashboard.jsx      # All groups + balance summary
            ├── GroupPage.jsx      # Expenses/Balances/Settlements/Members tabs
            ├── NewExpense.jsx     # Create expense with split modes
            ├── ExpenseDetail.jsx  # Split detail + real-time chat
            └── EditExpense.jsx
```

---

## Local Setup

### Prerequisites
- Node.js 18+
- npm

### 1. Backend

```bash
cd backend
npm install
```

The `.env` file is already configured for SQLite:
```
DATABASE_URL=file:./dev.db
JWT_SECRET=supersecretkey123
JWT_EXPIRES_IN=7d
PORT=5000
CLIENT_URL=http://localhost:5173
```

Run the database migration (creates `prisma/dev.db`):
```bash
npx prisma migrate dev --name init
```

Start the server:
```bash
npm run dev
```

Backend runs at **http://localhost:5000**

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**

### Verify it works
1. Open http://localhost:5173
2. Register a new account
3. Create a group, add another user, add an expense

---

## Deployment

### Backend → Railway

1. Push the repo to GitHub
2. Create a new Railway project → **Deploy from GitHub repo**
3. Set the root directory to `/backend`
4. Add environment variables in Railway dashboard:
   ```
   DATABASE_URL=file:./dev.db
   JWT_SECRET=<generate a strong secret>
   JWT_EXPIRES_IN=7d
   CLIENT_URL=https://your-frontend.vercel.app
   ```
5. In Railway settings → add a **Volume** mounted at `/app/prisma` so `dev.db` persists across restarts
6. Add a start command: `npx prisma migrate deploy && node src/index.js`

### Frontend → Vercel

1. Import the GitHub repo to Vercel
2. Set root directory to `/frontend`
3. Add environment variables:
   ```
   VITE_API_URL=https://your-backend.railway.app
   VITE_SOCKET_URL=https://your-backend.railway.app
   ```
4. Deploy

---

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Create account |
| POST | /api/auth/login | Login |
| GET | /api/auth/me | Get current user |
| GET | /api/users/search?email= | Search users |
| GET | /api/users/me/balances | Personal balance across groups |
| GET | /api/groups | List my groups |
| POST | /api/groups | Create group |
| GET | /api/groups/:id | Group detail |
| PUT | /api/groups/:id | Update group |
| DELETE | /api/groups/:id | Delete group |
| POST | /api/groups/:id/members | Add member |
| DELETE | /api/groups/:id/members/:userId | Remove member |
| GET | /api/groups/:id/expenses | List expenses |
| POST | /api/groups/:id/expenses | Create expense |
| GET | /api/expenses/:id | Expense detail |
| PUT | /api/expenses/:id | Update expense |
| DELETE | /api/expenses/:id | Delete expense |
| GET | /api/groups/:id/balances | Group balances |
| GET | /api/groups/:id/settlements | List settlements |
| POST | /api/groups/:id/settlements | Record settlement |
| GET | /api/expenses/:id/messages | Chat history |

### Socket.io Events
```
Client → Server:
  join_expense  { expenseId }
  send_message  { expenseId, text, token }

Server → Client:
  new_message   { id, expenseId, userId, text, createdAt, user }
```

---

## AI Collaboration

This project was built end-to-end with Claude as the primary engineering collaborator. See:
- `AI_CONTEXT.md` — full working context, decisions, schema, and implementation notes
- `BUILD_PLAN.md` — product research, architecture, collaboration process, tradeoffs
- `PROMPTS.md` — key prompts used to drive the build

---

## Known Limitations

- SQLite does not support concurrent writes well; fine for demo/low traffic
- No image upload for avatars (initials-based fallback)
- No email notifications
- No push notifications
- No expense categories or tags
- Settlements do not auto-suggest optimal payment paths (Splitwise does this)
- No multi-currency conversion
