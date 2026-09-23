# a2d-pdf — Analog to Digital PDF

Upload a scanned PDF → Gemini AI digitalizes it → Get a pixel-perfect HTML replica that prints perfectly.

## Stack

| Layer    | Tech                        | Deploy        |
|----------|-----------------------------|---------------|
| Backend  | Python FastAPI              | Vercel        |
| Frontend | React + Vite                | Firebase      |
| AI       | Gemini 2.5 Flash            | Google AI     |

## GitHub Secrets Required

Go to **Settings → Secrets and variables → Actions** and add:

| Secret                      | Value                                              |
|-----------------------------|----------------------------------------------------|
| `GEMINI_API_KEY`            | Your Gemini API key from aistudio.google.com       |
| `VERCEL_TOKEN`              | From vercel.com → Settings → Tokens               |
| `FIREBASE_SERVICE_ACCOUNT`  | JSON from Firebase Console → Project Settings → Service Accounts |
| `VITE_API_URL`              | Your Vercel deployment URL e.g. `https://a2d-pdf.vercel.app` |

## Branch Rules

- `main` is protected — no direct pushes allowed
- All changes must come through a Pull Request
- PR must be approved before merge

## Local Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
GEMINI_API_KEY=your_key uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Deploy

Push to `main` via PR → GitHub Actions auto-deploys:
- Backend changes → Vercel
- Frontend changes → Firebase (`a2dpdf.web.app`)
