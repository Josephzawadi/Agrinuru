# AgriNuru

AgriNuru is an agricultural production and market decision support project. This initial foundation uses a React and TypeScript frontend with a Django REST API. It introduces the project and provides a health-check endpoint; authentication and agricultural workflows are not implemented yet.

## Requirements

- Python 3.12 or another version supported by Django 5.2
- Node.js LTS and npm
- PostgreSQL for the planned database, or SQLite for a quick local smoke test

## Start the backend (Windows PowerShell)

From the repository root, create and install into a virtual environment:

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

The example environment uses SQLite by default, so PostgreSQL is not required for the first smoke test. To use PostgreSQL, install and start PostgreSQL, create a database and user, then add a `DATABASE_URL` value to `backend/.env`, for example:

```text
DATABASE_URL=postgresql://agrinuru_user:your-password@127.0.0.1:5432/agrinuru
```

Keep real passwords and secret keys out of source control. The Django admin is available at `http://127.0.0.1:8000/admin/` after creating a superuser; admin workflows are not part of this phase.

## Start the frontend

In a second PowerShell terminal from the repository root:

```powershell
Set-Location frontend
 npm install
Copy-Item .env.example .env
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://localhost:5173/`. The landing page checks the backend health endpoint and displays whether the API is reachable. Its hero photograph and typefaces load from external sources and require an internet connection.

## Test the setup

- Backend health check: open `http://127.0.0.1:8000/api/health/`; expect JSON with `"status": "ok"`.
- Backend test: from `backend/`, run `.\.venv\Scripts\python.exe manage.py test`.
- Frontend production build: from `frontend/`, run `npm run build`.