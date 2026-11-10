# AgriNuru

AgriNuru is an agricultural production and market decision support project built with a React and TypeScript frontend and Django REST API. It currently supports farmer, farm, crop, and crop-linked production records. Authentication, weather integrations, and market-data workflows are not implemented yet.

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

## Production management

Phase 4 adds crop-linked activities, input usage, production expenses, and actual harvest records. CRUD collections are available at `/api/production/activities/`, `/api/production/inputs/`, `/api/production/expenses/`, and `/api/production/harvests/`. Each supports list, create, retrieve, and update. Production records are not hard-deleted: `POST /api/production/<collection>/<id>/void/` requires a reason and retains the record. Lists exclude voided records by default; use `?include_voided=true` to review history. Voided records cannot be edited and are excluded from summaries.

Production records reference existing crops; farm and farmer context is derived through each crop. Filters include `crop`, `farm`, `farmer`, `date_from`, and `date_to`. Activities represent completed work only. Activity, input-usage, and expense dates may precede planting when appropriate; completed records cannot be future-dated. Actual harvest dates cannot precede planting.

Input quantities must be positive and include a unit. Input purchase cost is recorded on the input-use record; production expenses are for other costs to avoid double counting. Costs are non-negative, use an explicit three-letter currency code, and default to KES. Totals are grouped by currency; the application does not convert currencies.

Actual harvest quantities may be zero but not negative, and use kilograms or tonnes. Production summaries normalize compatible harvest quantities to kilograms for expected-versus-actual comparison. A missing expected quantity is not treated as zero. Date-filtered harvest summaries are identified as period-limited and are not presented as full-season comparisons.

The Production page provides activity, input, expense, harvest, and summary sections. Summaries exclude voided records and keep costs grouped by currency.

## Authentication foundation

The API uses Django session authentication. Register with a username, email address, full name, phone number, county, sub-county, and password at `POST /api/auth/register/`, then sign in at `POST /api/auth/login/`. Registration creates a new farmer profile linked to the account, using English as the preferred language. It never claims or links an existing profile based on email or phone. `GET /api/auth/me/` returns the signed-in account, and `POST /api/auth/logout/` ends its session. Obtain a CSRF cookie/token from `GET /api/auth/csrf/` before unsafe requests. The React API client sends session cookies and CSRF headers; do not store passwords or session identifiers in browser storage.

The frontend and backend should use the same local hostname so browser session cookies remain same-site. The default frontend API URL is `http://localhost:8000`; open Vite at `http://localhost:5173/`. For a different deployment origin, configure `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` with the exact trusted origins and use HTTPS in production.

Authenticated, linked farmer accounts can access only their own farmer profile, farms, crops, and crop-linked production records and summaries. Production record crop references are restricted to the farmer's own crops. Unlinked accounts are denied access to farmer data. AgriNuru staff (members of the AgriNuru Staff group) and administrators (Django superusers) can access records across farmers. Only administrators can assign or remove the AgriNuru Staff role. Existing unassigned profiles remain unassigned until authorised staff explicitly link them; public registration creates a separate profile for the new account.

## Test the setup

- Backend health check: open `http://127.0.0.1:8000/api/health/`; expect JSON with `"status": "ok"`.
- Backend test: from `backend/`, run `.\.venv\Scripts\python.exe manage.py test`.
- Frontend production build: from `frontend/`, run `npm run build`.

## Planned machine learning and data workspace

The `ml/` directory contains the project's organised raw agricultural datasets and a place for future machine-learning work. Planned capabilities are:

- Crop recommendation from soil nutrient and environmental conditions.
- Crop-yield prediction using historical agricultural and environmental information.
- Kenyan agricultural commodity market-price forecasting from historical prices.

These are planned development components; AgriNuru does not currently train or serve these models. See [ml/README.md](./ml/README.md) for the workspace layout and [ml/data/README.md](./ml/data/README.md) for dataset sources, schemas, record counts, and known limitations. Original raw files are retained unchanged; processed data and generated model artifacts are not committed by default.