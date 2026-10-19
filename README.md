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

## Farmer and farm management

The Phase 2 API exposes `GET`, `POST`, `GET /<id>/`, `PATCH /<id>/`, and `DELETE /<id>/` operations at `/api/farmers/` and `/api/farms/`. Farm records reference an existing farmer. A farmer with registered farms cannot be deleted; the API returns HTTP 409 until those farms are removed or reassigned.

The Farmer and Farms navigation pages use these API endpoints directly. Farmer details include name, phone number, email, county, sub-county, and preferred language; farm details include farmer, name, location, and approximate size in acres.

## Crop management

The Phase 3 API provides `GET`, `POST`, `GET /<id>/`, `PATCH /<id>/`, and `DELETE /<id>/` operations at `/api/crops/`. Every crop belongs to an existing farm. Crop records include a name, optional variety, farm, planting and expected harvest dates, cultivated area in acres, growth stage, optional expected harvest quantity and its unit, and creation/update timestamps.

Crop names, farms, dates, and cultivated areas are required. Cultivated area must be positive, fit within the farm's remaining registered area, and combined crop allocations cannot exceed the farm size. Expected harvest cannot precede planting. Expected harvest quantity may be omitted; when supplied it must be non-negative and paired with an explicit unit (kilograms or tonnes). Growth stage uses defined choices and is farmer-recorded information, not automatically verified.

Farms with crop records cannot be deleted. A farm-size update is rejected if it would fall below the total area allocated to its crops; existing crop records are never silently changed or deleted to accommodate a resize.

The Crops navigation page loads real crop and farm records from the API. Register a farm before creating its crop records.

**Security notice:** These CRUD endpoints are currently unauthenticated and are intended only for local development. Do not expose them publicly or deploy them to a public environment until authentication, authorization, and access controls are implemented.

## Test the setup

- Backend health check: open `http://127.0.0.1:8000/api/health/`; expect JSON with `"status": "ok"`.
- Backend test: from `backend/`, run `.\.venv\Scripts\python.exe manage.py test`.
- Frontend production build: from `frontend/`, run `npm run build`.