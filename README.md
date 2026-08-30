# SIH Backend — Business API Service

Owns: auth, project CRUD, assignment, and the status workflow
(`PLANNED → ASSIGNED → IN_PROGRESS → COMPLETED → VERIFIED`).

Does NOT own: priority score calculation, progress analytics, or running the
AI/vision-LLM model — that's the Analytics API side (Nikita / AI module).
This service only stores whatever result that side sends back
(see `PATCH /api/projects/:id/evidence/:evidenceId/ai-result`).

## Folder structure

```
backend/
├── config/db.js              MongoDB connection
├── models/                   User.js, Project.js (schemas)
├── middleware/                auth (JWT check) + error handling
├── controllers/               actual logic per route
├── routes/                    URL -> controller wiring
├── utils/generateToken.js
├── server.js                  entry point
└── .env.example                template — copy to .env
```

## 1. Run it locally

```bash
cd backend
npm install
cp .env.example .env
```

Fill in `.env` (see "Where to get each value" below), then:

```bash
npm run dev      # nodemon, auto-restarts on save
# or
npm start
```

Check it's alive:
```bash
curl http://localhost:5000/api/health
```

### Quick local test flow

```bash
# Register an officer
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Officer One","email":"o1@test.com","password":"pass123","role":"OFFICER"}'

# Copy the "token" from the response, then create a project
curl -X POST http://localhost:5000/api/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"title":"Pothole repair - Ward 4","location":{"lat":16.5,"lng":80.6}}'
```

## 2. Where to get each value (this is the "security/API" part you're handling)

| .env variable | Where it comes from |
|---|---|
| `MONGO_URI` (local) | Run MongoDB locally, or just use Atlas for local dev too: `mongodb://127.0.0.1:27017/sih_db` if you install MongoDB Community Server locally |
| `MONGO_URI` (deploy) | [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register) → free M0 cluster → Database → Connect → "Drivers" → copy the connection string → replace `<password>` with your DB user's password |
| `JWT_SECRET` | Generate it yourself, don't make one up by hand: `node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"` — paste the output in |
| `PORT` | `5000` locally. On Render, Render sets its own `PORT` env var automatically — your code already reads `process.env.PORT` so no change needed |
| `CORS_ORIGIN` | Local: `http://localhost:5173` (or whatever port your frontend runs on). Deploy: your deployed frontend URL, e.g. `https://your-app.vercel.app` |

**Atlas network access:** when you create the Atlas cluster, under "Network Access" add `0.0.0.0/0` (allow from anywhere) for the hackathon — it's not ideal for production but is the standard hackathon shortcut so Render can reach it without IP whitelisting headaches.

## 3. Auth model (already built in)

- Passwords are hashed with bcrypt before saving — never stored in plain text.
- Login returns a JWT (`jsonwebtoken`), valid 7 days.
- Protected routes require `Authorization: Bearer <token>` header.
- Role-based access via `authorize("OFFICER", "ADMIN")` in routes — citizens can submit evidence but can't create/assign/verify projects.

## 4. One thing to decide with Nikita: the AI callback endpoint

`PATCH /api/projects/:id/evidence/:evidenceId/ai-result` is how the AI/analytics
service writes its result back onto a project's evidence. Right now it's locked to
`ADMIN` role as a placeholder. Two real options:

- **Simple (fine for a hackathon):** give the AI service a dedicated ADMIN user account + its own JWT, generated once and hardcoded into that service's env.
- **Cleaner:** add a separate `SERVICE_API_KEY` env var, check it via a header (`x-service-key`) in a small middleware, and skip JWT entirely for this one internal route.

I didn't build the second one in — say the word if you want it, it's a ~15 line middleware.

## 5. Deploy to Render

1. Push this `backend/` folder to a GitHub repo (or a subfolder of your monorepo).
2. On [Render](https://render.com) → New → Web Service → connect your GitHub repo.
3. If `backend/` is a subfolder, set **Root Directory** to `backend`.
4. Build command: `npm install`
5. Start command: `npm start`
6. Under Environment, add the same variables as your `.env` — `MONGO_URI`, `JWT_SECRET`, `CORS_ORIGIN` (set this to your deployed frontend's real URL, not localhost). Don't set `PORT` — Render injects it.
7. Deploy. Test with `https://<your-service>.onrender.com/api/health`.

Free-tier Render services spin down after inactivity and take ~30–50s to wake up on the first request — worth knowing before a live demo, hit the health endpoint a minute before you go up.

## API summary

| Method | Route | Access |
|---|---|---|
| POST | `/api/auth/register` | public |
| POST | `/api/auth/login` | public |
| GET | `/api/auth/me` | authenticated |
| POST | `/api/projects` | OFFICER/ADMIN |
| GET | `/api/projects` | authenticated |
| GET | `/api/projects/:id` | authenticated |
| PATCH | `/api/projects/:id` | OFFICER/ADMIN |
| DELETE | `/api/projects/:id` | ADMIN |
| POST | `/api/projects/:id/assign` | OFFICER/ADMIN |
| PATCH | `/api/projects/:id/status` | OFFICER/ADMIN |
| GET | `/api/projects/:id/status-history` | authenticated |
| POST | `/api/projects/:id/evidence` | authenticated |
| PATCH | `/api/projects/:id/evidence/:evidenceId/ai-result` | ADMIN (AI service) |
