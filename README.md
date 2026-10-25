# Lead Capture API

A backend API built with **Python and FastAPI** to capture, validate, persist, and classify potential clients using an LLM.

This project is part of my **Road to Agentic AI**, focused on learning the backend foundations required to build reliable AI-powered systems and automation.

The project evolved from a simple SQLite API into a containerized, tested, authenticated, PostgreSQL-backed API with migrations and public deployment.

---

## Architecture

```text
Client (Postman / cURL)
          │
          ▼
       FastAPI
          │
     API Key Auth
          │
     Pydantic Validation
          │
    Depends(get_db)
          │
          ▼
      PostgreSQL
          │
          ▼
         LLM
          │
     Hot / Cold
     or pending
```

---

## Tech Stack

* **Python**
* **FastAPI**
* **Pydantic**
* **SQLAlchemy**
* **PostgreSQL**
* **Alembic**
* **LLM API**
* **Pytest**
* **Docker / Docker Compose**
* **Render**
* **python-dotenv**
* **Python Logging**

---
### LLM Cost Estimation

The API estimates LLM inference costs for lead classification (`POST /leads`) and assistant interactions (`POST /assistant/ask`) using token usage reported by the model.

**Cost calculation**

The estimated cost is calculated using the model's input and output token usage:

- Input tokens: charge_input per million tokens.
- Cached input tokens: charged_cached per million tokens, when reported by the provider.
- Output tokens: charge_output per million tokens.

The calculation is performed for each model response. For assistant interactions involving multiple model calls, the individual costs are accumulated to obtain the estimated total cost of the interaction.

**Logging**

The application logs input, output, and total token counts, the operation performed, the model used, and the estimated cost in USD. For assistant interactions, it also logs the accumulated estimated cost associated with the conversation ID.

**Limitations**

These values are estimates based on the configured model pricing and reported token usage. They do not represent a complete operational cost calculation and exclude infrastructure, database, and other service expenses. Model pricing may change over time.

---

## API Endpoints

All endpoints require an API key through the `X-API-Key` header.

| Method  | Endpoint      | Description                   |
| ------- | ------------- | ----------------------------- |
| `POST`  | `/leads`      | Create and classify a lead    |
| `GET`   | `/leads`      | Get a paginated list of leads |
| `GET`   | `/leads/{id}` | Get a specific lead           |
| `PATCH` | `/leads/{id}` | Manually update a lead        |

### `POST /leads`

Creates a lead and attempts to classify it with an LLM.

Required fields:

```json
{
  "name": "Juan",
  "email": "juan@example.com",
  "phone": "8095551234",
  "request": "Website design",
  "notes": ""
}
```

Possible classification:

```text
Hot
Cold
pending
```

If the LLM fails, the lead is still stored with `pending` status.

### `GET /leads`

Returns leads using pagination:

```text
GET /leads?page=1&limit=10
```

### `GET /leads/{id}`

Returns a specific lead.

Returns `404 Not Found` if the lead does not exist.

### `PATCH /leads/{id}`

Allows manual updates to a lead, including changing its temperature when its previous classification is `pending`.

---

## Authentication

API key authentication was added to all four endpoints.

```http
X-API-Key: your_api_key
```

Responses:

* `401 Unauthorized` — API key missing
* `403 Forbidden` — invalid API key

The key is stored through environment variables.

---

## Safety

### Human-in-the-Loop (HITL)

The `update_lead_temperature` tool requires explicit confirmation (`requires_confirmation=True`) and is never executed automatically by the LLM.

When the LLM requests a temperature change, the application stores it as a `PendingAction` with `pending` status. The lead remains unchanged until an API client explicitly approves or rejects the request. Approved actions are executed; rejected actions are not.

This protection applies specifically to LLM-initiated changes. The `PATCH /leads/{id}` endpoint still allows direct updates through the API without this approval workflow.

Currently, action management relies on API key authentication. Role-based permissions and individual operator identification are not implemented and remain potential future improvements.

---

## Database & Migrations

The project was migrated from **SQLite to PostgreSQL**.

Database sessions are managed through FastAPI dependency injection using:

```python
Depends(get_db)
```

instead of manually creating sessions inside each endpoint.

**Alembic** is used for version-controlled database schema migrations.

A separate migration script is also included under:

```text
migrations/
```

to support transferring existing SQLite data to PostgreSQL.

---

## Error Handling

The API handles failures at different stages:

| Scenario              | Response                    |
| --------------------- | --------------------------- |
| Missing API key       | `401 Unauthorized`          |
| Invalid API key       | `403 Forbidden`             |
| Invalid/missing data  | `422 Unprocessable Entity`  |
| Duplicate email/phone | `409 Conflict`              |
| Lead not found        | `404 Not Found`             |
| LLM failure           | Lead preserved as `pending` |

Database failures use `rollback()` to keep the session consistent.

---

## Logging

`print()` statements were replaced with structured Python logging.

The application uses:

```text
INFO
WARNING
ERROR
```

for application events, warnings, and unexpected failures.

---

## Testing

Automated testing was implemented with **Pytest**.

Tested scenarios include:

* Successful lead creation — `201`
* Duplicate email/phone — `409`
* Invalid data — `422`
* Missing API key — `401`
* Invalid API key — `403`

---

## Docker

The application is containerized with:

```text
Dockerfile
docker-compose.yml
.env.example
```

Docker Compose runs:

```text
API
PostgreSQL
```

The PostgreSQL service includes a **health check**, ensuring the database is ready before the API starts.

The entire application can be started with:

```bash
docker compose up
```

or rebuilt with:

```bash
docker compose up --build
```

No additional manual startup steps are required.

---

## Deployment

The API is publicly deployed using **Render**.

**Live API:**

https://lead-capture-api-hut0.onrender.com

**Interactive documentation:**

https://lead-capture-api-hut0.onrender.com/docs

---

## Running Locally

### Clone

```bash
git clone https://github.com/SoyColde/lead_capture_api.git
cd lead_capture_api
```

### Install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Configure environment

Create a `.env` file based on `.env.example`.

```env
LLM_API_KEY=your_api_key
API_KEY=your_api_key
DATABASE_URL=your_database_url
```

### Run migrations

```bash
alembic upgrade head
```

### Start API

```bash
uvicorn main:app --reload
```

API:

```text
http://127.0.0.1:8000
```

Docs:

```text
http://127.0.0.1:8000/docs
```

---

## What I Learned

This project helped me practice:

* REST APIs and HTTP
* FastAPI & Pydantic
* SQLAlchemy & PostgreSQL
* Dependency Injection with `Depends`
* Database transactions and `rollback()`
* Alembic migrations
* API key authentication
* Pagination and CRUD operations
* LLM integration and failure handling
* Logging
* Automated testing with Pytest
* Docker & Docker Compose
* Database health checks
* Deployment

---

## Project Goal

The long-term goal is to understand the backend foundations behind **AI agents and automation systems**.

```text
Receive information
        ↓
Understand it
        ↓
Make a decision
        ↓
Call external systems
        ↓
Perform an action
        ↓
Store the result
        ↓
Continue the workflow
```

This API is one of the first steps in my **Road to Agentic AI**.

---

## Author

**Colde**

ITLA — Artificial Intelligence

**Road to Agentic AI**
