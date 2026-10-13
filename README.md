# Notes to Quiz

> Paste your study notes or upload a PDF and get a concise summary plus a 10-question multiple-choice quiz that gets harder as you go.

![Status](https://img.shields.io/badge/status-in%20development-orange)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-database-4169E1?logo=postgresql&logoColor=white)

Notes to Quiz is a full-stack study tool. You give it your material (pasted text or a text-based PDF), an LLM turns it into a short summary and a structured revision quiz, and every set you generate is saved to your account so you can come back to it later.

> **Project status:** under active development and not yet deployed. This README covers running the project locally.

<!-- Add a screenshot or short GIF of the app here:
![Notes to Quiz screenshot](docs/screenshot.png) -->

---

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [Author](#author)

---

## Features

- **Two ways to add material:** paste notes (100 to 8,000 characters) or drag and drop a PDF (up to 10 MB)
- **Summary plus 10 questions:** a 3 to 5 sentence summary and exactly 10 multiple-choice questions per set
- **Rising difficulty:** questions 1-3 are easy, 4-7 medium, 8-10 hard
- **Grounded in your notes:** the model is instructed to use only the supplied material, with no outside facts
- **Instant feedback:** pick an answer to see whether it was right, with the correct option highlighted and a short explanation
- **Validated output:** every model response is parsed and checked against a strict schema; if it fails, the model gets one retry with the validation error
- **Accounts and saved sets:** sign in with Clerk; each user sees only their own library (latest 20 sets)
- **Cold-start friendly:** the frontend pings the backend on load and shows a "waking the server" notice, which suits free-tier hosting

---

## How It Works

```text
 React + Vite frontend  ──(Clerk JWT in Authorization header)──►  FastAPI backend
 (paste notes / PDF)                                                   │
                                                     ┌─────────────────┼──────────────────┐
                                                     ▼                 ▼                  ▼
                                              Clerk verifies     pypdf extracts      Groq LLM (OpenAI-
                                              the session token  PDF text            compatible API)
                                                                                           │
                                                                       JSON → Pydantic validation (1 retry)
                                                                                           │
                                                                                           ▼
                                                                          PostgreSQL (SQLAlchemy)
                                                                          stores the set per user
```

1. The user signs in through Clerk on the frontend.
2. The frontend sends notes (or a PDF) to the backend with the user's Clerk token.
3. The backend verifies the token, extracts text from the PDF if needed, and prompts the LLM.
4. The response is extracted, parsed, and validated (10 questions, 4 options each, one correct answer, valid difficulty).
5. The set is saved to PostgreSQL under the user's ID and returned to the UI.

---

## Tech Stack

| Layer          | Technology                                              |
| -------------- | ------------------------------------------------------- |
| Frontend       | React 19, Vite 8, Oxlint                                |
| Auth           | Clerk (`@clerk/clerk-react` on the client, `clerk-backend-api` on the server) |
| Backend        | Python, FastAPI, Uvicorn                                |
| Validation     | Pydantic 2                                              |
| Database       | PostgreSQL via SQLAlchemy 2 and psycopg2                |
| LLM            | Groq, called through the OpenAI Python SDK (default model `openai/gpt-oss-20b`) |
| PDF parsing    | pypdf                                                   |

---

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI app, routes, PDF text extraction
│   │   ├── llm.py         # Prompt, model call, JSON extraction and validation
│   │   ├── auth.py        # Clerk token verification (FastAPI dependency)
│   │   └── db.py          # SQLAlchemy engine, session, NoteSet model
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.jsx        # Create / Saved tabs, paste and PDF inputs
    │   ├── QuizCard.jsx   # Summary and interactive question cards
    │   ├── api.js         # Authenticated API client hook
    │   └── main.jsx       # ClerkProvider setup
    ├── package.json
    └── .env.example
```

---

## Getting Started

### Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- A PostgreSQL database (local, or a hosted one such as Neon or Supabase)
- A [Clerk](https://clerk.com) application (publishable key, secret key, and optionally the JWT public key)
- A [Groq](https://console.groq.com) API key

### 1. Clone

```bash
git clone https://github.com/Raheeemm/Notes-to-quiz.git
cd Notes-to-quiz
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install pypdf                # PDF support; see note below
cp .env.example .env             # then fill in the values (see Environment Variables)
uvicorn app.main:app --reload --port 8000
```

The API is now at <http://localhost:8000>, with interactive docs at <http://localhost:8000/docs>. Tables are created automatically on startup.

> **Note:** `pypdf` is imported by the backend but is not yet listed in `requirements.txt`, hence the extra install step. Once it is added to the file you can drop that line.

### 3. Frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env             # then fill in the values
npm run dev
```

Open the URL Vite prints (by default <http://localhost:5173>) and sign in.

### Useful frontend scripts

| Command           | Description                    |
| ----------------- | ------------------------------ |
| `npm run dev`     | Start the dev server           |
| `npm run build`   | Production build into `dist/`  |
| `npm run preview` | Preview the production build   |
| `npm run lint`    | Lint with Oxlint               |

---

## Environment Variables

### Backend (`backend/.env`)

| Variable            | Required | Description                                                                 |
| ------------------- | -------- | --------------------------------------------------------------------------- |
| `DATABASE_URL`      | Yes      | PostgreSQL connection string, e.g. `postgresql://user:pass@host/db?sslmode=require` |
| `GROQ_API_KEY`      | Yes      | Groq API key                                                                |
| `CLERK_SECRET_KEY`  | Yes      | Clerk secret key. The server refuses to start without it                    |
| `CLERK_JWT_KEY`     | No       | Clerk JWT public key (PEM). Enables fast local token verification; without it the SDK fetches Clerk's JWKS over the network |
| `LLM_MODEL`         | No       | Groq model ID. Default: `openai/gpt-oss-20b`                                |
| `ALLOWED_ORIGINS`   | No       | Comma-separated frontend origins for CORS and Clerk. Default: `http://localhost:5173` |

### Frontend (`frontend/.env`)

| Variable                     | Required | Description                                           |
| ---------------------------- | -------- | ----------------------------------------------------- |
| `VITE_CLERK_PUBLISHABLE_KEY` | Yes      | Clerk publishable key                                 |
| `VITE_API_URL`               | No       | Backend URL. Default: `http://localhost:8000`         |

Never commit real keys. `.env` files are already git-ignored.

---

## API Reference

All routes except `/api/health` require a valid Clerk session token: `Authorization: Bearer <token>`.

| Method | Route               | Description                                                              |
| ------ | ------------------- | ------------------------------------------------------------------------ |
| GET    | `/api/health`       | Health check. Returns `{"status": "ok"}`                                 |
| POST   | `/api/generate`     | Generate a set from pasted notes. JSON body: `{"text": "..."}` (100 to 8,000 characters) |
| POST   | `/api/generate-pdf` | Generate a set from an uploaded PDF. Multipart form field `file` (PDF, max 10 MB) |
| GET    | `/api/history`      | The signed-in user's 20 most recent sets                                 |

**Example response** (`/api/generate`):

```json
{
  "id": 12,
  "summary": "A 3 to 5 sentence summary of the notes...",
  "questions": [
    {
      "question": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 0,
      "explanation": "Why this answer is correct.",
      "difficulty": "easy"
    }
  ],
  "created_at": "2026-10-13T16:30:00Z"
}
```

`questions` always contains exactly 10 items. `/api/generate-pdf` also returns `source_name` (the uploaded file name).

---

## Limitations

- PDFs must contain selectable text. Scanned or image-only PDFs are rejected.
- Input is capped at 8,000 characters. Longer PDFs are truncated to the first 8,000 characters of extracted text.
- Output quality depends on the LLM and on how clear the source material is. Questions are generated from your notes only, but always sanity-check anything you plan to rely on.
- Sign-in is required; there is no anonymous mode.

---

## Roadmap

- [ ] Deploy the frontend and backend
- [ ] OCR support for scanned PDFs
- [ ] Handle longer documents (chunking instead of truncating)
- [ ] Score quizzes and track results over time
- [ ] Delete and rename saved sets
- [ ] Automated tests (backend validation logic and API routes)

---

## Author

**Abdul Raheem**, [@Raheeemm](https://github.com/Raheeemm)
