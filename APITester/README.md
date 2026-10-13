# Customer List API

A small FastAPI app with a customer list UI that refreshes every five seconds,
plus JSON endpoints for creating, reading, updating, and deleting customers.

## Run locally

Requires Python 3.10 or newer.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000> for the customer list and
<http://127.0.0.1:8000/docs> for interactive API documentation. If
`DATABASE_URL` is not set, the app uses `customers.db` in the working directory.
Use <http://127.0.0.1:8000/import> to import CSV changes.

## Project layout

- `app/main.py` creates the FastAPI app, initializes the database, and serves the pages and static assets.
- `app/routers/customers.py` contains customer CRUD endpoints.
- `app/routers/customer_csv.py` contains CSV import and export endpoints.
- `app/dependencies.py` provides the request-scoped database session.
- `static/` contains the HTML pages and their shared/page-specific CSS and JavaScript.
- `tests/test_api.py` covers API behavior and static asset delivery.

## Start from VS Code

Open the **Run and Debug** view, select **Customer API**, then click the green
play button (or press `F5`). This launches Uvicorn with reload enabled in the
integrated terminal. Make sure the VS Code Python extension is using this
workspace's `.venv` interpreter and the dependencies above are installed.

## SQL Server

Install Microsoft ODBC Driver 18 for SQL Server, then set `DATABASE_URL` to a
SQLAlchemy `mssql+pyodbc` URL before starting the app. For example:

```powershell
$env:DATABASE_URL = "mssql+pyodbc://user:password@server/database?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes"
python -m uvicorn app.main:app --reload
```

URL-encode special characters in usernames and passwords. Keep real connection
details in environment variables (or a local, untracked `.env` file loaded
with `python -m uvicorn app.main:app --reload --env-file .env`); do not commit
credentials.

At startup, SQLAlchemy's `create_all` creates the `customers` table if it does
not exist. This is code-first table creation, not a schema migration system:
existing tables are not altered when the model changes.

## Customer fields

- `customer_number`: required, unique key (up to 50 characters)
- `customer_name`: required (up to 200 characters)
- `customer_type`: required (up to 100 characters)
- `customer_category`: required (up to 100 characters)

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/customers` | List customers |
| `GET` | `/api/customers/export` | Download all customers as an import-ready CSV |
| `GET` | `/export` | Direct download URL for the import-ready CSV |
| `POST` | `/api/customers` | Create a customer |
| `GET` | `/api/customers/{customer_number}` | Read one customer |
| `PUT` | `/api/customers/{customer_number}` | Update a customer's name, type, and category |
| `DELETE` | `/api/customers/{customer_number}` | Delete a customer |
| `POST` | `/api/customers/import` | Apply Create, Update, and Delete actions from a multipart CSV upload (`file` field) |

The customer number is supplied when creating a record and cannot be changed
by the update endpoint. Duplicate customer numbers return `409 Conflict`;
missing records return `404 Not Found`.

## CSV import

The import page accepts UTF-8 CSV files up to 10 MB with this exact header row:

```csv
Action,Customer Number,Customer Name,Customer Type,Customer Category
```

Each row's Action must be `Create`, `Update`, or `Delete` (case-insensitive).
Create requires all four customer fields and fails if the customer number
already exists. Update requires an existing customer number and all three
customer details. Delete requires only the customer number; its other fields
can be blank. Rows are processed independently: successful rows are committed,
and invalid rows are reported without undoing other successes. The import
response includes per-row results and success/failure counts.

The customer list's **Download customer data CSV** link exports all current
customers using the same template, with each row marked `Create`. The resulting
file can be uploaded to the import page to populate a fresh/empty database.
