# School Management System — Backend API

A role-based school management REST API built with **FastAPI** and **PostgreSQL**.

Designed to be sold and deployed per client school, where each school enables only the
modules it needs. The codebase is organised router-per-module so that adding or removing
a feature means adding or removing one router file — never editing unrelated code.

> **Status:** backend in active development. 37 endpoints implemented and manually
> verified. Frontend not started yet.

---

## Features

- **JWT authentication** with Argon2 password hashing
- **Role-based authorization** — student, teacher, management, principal
- **Role hierarchy enforcement** — principals manage all roles, management may only
  manage students and teachers
- **Student management** — create, list, update, view own profile, view deactivated
- **Teacher management** — create, list, update, view deactivated
- **Teacher assignments** — link a teacher to a section and subject
- **Classes, sections and subjects** — academic structure CRUD
- **Soft deactivation** — accounts are deactivated, never destroyed, and keep their roles
  so they can be restored intact

---

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.14 |
| Framework | FastAPI |
| Database | PostgreSQL, accessed with `psycopg` v3 |
| Data access | Raw parameterised SQL — **no ORM, deliberately** |
| Validation | Pydantic v2 |
| Auth | PyJWT |
| Passwords | `pwdlib` with Argon2 |
| Config | `python-dotenv` |

Raw SQL is a deliberate choice: it keeps the queries explicit and readable, and avoids
hiding the relational model behind an abstraction layer.

---

## Project structure

```
backend/
├── main.py                    # app setup, login endpoints, router registration
├── database.py                # get_db() dependency, reads DATABASE_URL
│
├── auth/
│   ├── security.py            # hashing, authenticate_user, JWT create/verify
│   └── dependencies.py        # require_role() and all role-check dependencies
│
├── schemas/                   # Pydantic request/response models
│   ├── user.py
│   ├── student.py
│   ├── teacher.py
│   ├── academic.py            # classes + sections
│   ├── subject.py
│   └── assignment.py
│
├── routers/                   # HTTP layer — paths, permissions, responses
│   ├── students.py
│   ├── teachers.py
│   ├── teacher_assignments.py
│   ├── users.py               # user CRUD + role assign/remove
│   ├── leadership_staff.py    # principals, management listings
│   ├── academic.py            # classes + sections
│   └── subjects.py
│
└── services/                  # Business logic — validation, multi-table transactions
    ├── student_service.py
    └── teacher_service.py
```

**Layering:** `Router` handles HTTP concerns → `Service` handles business logic and
multi-table transactions → raw SQL touches the database. Multi-step writes belong in a
service; simple reads live in the router.

---

## Database design

```
users              id, username, password_hash, is_active
profiles           id, user_id, name
roles              id, role_name
user_roles         user_id, role_id              (many-to-many)
teachers           id, user_id, teacher_id
students_new       id, user_id, student_id, section_id
classes            id, class_name
sections           id, class_id, section_name
subjects           id, subject_name
teacher_assignments id, teacher_id, section_id, subject_id
```

```
users ──┬── profiles              (name lives here, centralised)
        ├── user_roles ── roles
        ├── teachers ── teacher_assignments ── sections, subjects
        └── students_new ── sections ── classes
```

Two conventions worth knowing:

- **Names live only in `profiles.name`**, reached by JOIN. They are never duplicated onto
  `teachers` or `students_new`.
- **`id` is not the same as the business identifier.** `teachers.id` is the numeric
  primary key; `teachers.teacher_id` is the human-facing code such as `T001`. The same
  applies to `students_new`. Foreign keys reference the numeric `id`.

---

## Authentication & authorization

### JWT is identity, the database is truth

```
JWT ──> user_id ──> query PostgreSQL for CURRENT roles ──> authorize
```

The token carries a `roles` claim, but **authorization never trusts it**. Every protected
request re-queries `user_roles` and `users.is_active`.

This closes a real vulnerability: previously, a user whose `principal` role had been
revoked could keep acting as a principal until their token expired. Now, role changes and
deactivations take effect on the very next request.

### Role hierarchy

| Actor | Can assign / remove | Cannot assign / remove |
|---|---|---|
| **principal** | student, teacher, management, principal | — |
| **management** | student, teacher | management, principal |

Additional safeguards:

- The last remaining active principal cannot be removed.
- Management cannot deactivate principal or management accounts.
- Roles cannot be assigned to an inactive user.
- A role cannot be assigned twice or removed if not held.

### Deactivation semantics

- `DELETE /users/{username}` sets `is_active = FALSE` only. **Roles are preserved**, so
  the account can later be restored intact.
- `DELETE /users/{username}/roles/{role}` is the endpoint that actually removes a role.

---

## Getting started

### Prerequisites

- Python 3.14+
- PostgreSQL 16+

### Installation

```bash
git clone <your-repo-url>
cd School-management-system

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
```

Then edit `.env`:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string in psycopg keyword/value format |
| `SECRET_KEY` | Secret used to sign JWTs — generate a long random value |

Generate a secret key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Running

Run from the **project root**, not from inside `backend/`:

```bash
uvicorn backend.main:app --reload
```

| | |
|---|---|
| API | http://127.0.0.1:8000 |
| Interactive docs (Swagger) | http://127.0.0.1:8000/docs |

To try protected endpoints in Swagger, click **Authorize** and log in — that uses the
`/token` endpoint and applies the bearer token to every subsequent request.

---

## API overview

37 operations. Full interactive reference at `/docs`.

**Auth**

| Method | Path | Access |
|---|---|---|
| `GET` | `/` | public |
| `POST` | `/login` | public — JSON body |
| `POST` | `/token` | public — OAuth2 form, used by Swagger Authorize |
| `GET` | `/verify-token` | authenticated |

**Students**

| Method | Path | Access |
|---|---|---|
| `GET` | `/students` | management, principal |
| `POST` | `/students` | management, principal |
| `GET` | `/students/me` | student |
| `GET` | `/students/deactivated` | management, principal |
| `GET` | `/students/{student_id}` | management, principal |
| `PUT` | `/students/{student_id}` | management, principal |

**Teachers**

| Method | Path | Access |
|---|---|---|
| `GET` | `/teachers` | management, principal |
| `POST` | `/teachers` | management, principal |
| `GET` | `/teachers/deactivated` | management, principal |
| `GET` | `/teachers/{teacher_id}` | management, principal |
| `PUT` | `/teachers/{teacher_id}` | management, principal |

**Teacher assignments**

| Method | Path | Access |
|---|---|---|
| `GET` | `/teacher-assignments` | management, principal |
| `POST` | `/teacher-assignments` | management, principal |
| `GET` | `/teacher-assignments/{teacher_id}` | management, principal |
| `PUT` | `/teacher-assignments/{assignment_id}` | management, principal |
| `DELETE` | `/teacher-assignments/{assignment_id}` | management, principal |

**Users & roles**

| Method | Path | Access |
|---|---|---|
| `GET` | `/users` | management, principal |
| `POST` | `/users` | management, principal |
| `GET` | `/users/{username}` | management, principal |
| `DELETE` | `/users/{username}` | management, principal — deactivates |
| `POST` | `/users/{username}/roles` | management, principal — hierarchy enforced |
| `DELETE` | `/users/{username}/roles/{role}` | management, principal — hierarchy enforced |

**Leadership & staff**

| Method | Path | Access |
|---|---|---|
| `GET` | `/principals` | principal |
| `GET` | `/management` | management, principal |

**Academic structure**

| Method | Path | Access |
|---|---|---|
| `GET` | `/classes` | authenticated |
| `POST` | `/classes` | management, principal |
| `GET` | `/sections` | authenticated |
| `POST` | `/sections` | management, principal |
| `GET` | `/subjects` | authenticated |
| `POST` | `/subjects` | management, principal |
| `GET` | `/subjects/{subject_id}` | authenticated |
| `PUT` | `/subjects/{subject_id}` | management, principal |
| `DELETE` | `/subjects/{subject_id}` | management, principal — blocked if in use |

---

## Roadmap

**Next up**

- [ ] Bulk import — upload a CSV of ~300 students or teachers, reusing the existing
      service functions, collecting per-row successes and failures so one bad row does
      not abort the rest
- [ ] Basic frontend — login, role-based dashboards, student and teacher lists and forms,
      structured modularly from the start

**Before production**

- [ ] JWT expiry — `create_access_token()` does not yet set an `exp` claim
- [ ] CORS middleware, required before a browser frontend can call the API
- [ ] Password strength validation
- [ ] Pagination on list endpoints
- [ ] Support non-numeric class names such as "Nursery" and "LKG" — several `ORDER BY`
      clauses currently cast `class_name` to integer
- [ ] Automated test suite

**Future modules**

Attendance · Marks and report cards · Timetable · Per-role dashboards ·
Notifications (email, SMS, WhatsApp) · Fee management · Parent access ·
Reports and analytics · Cloud deployment

---

## Development notes

Verify no endpoints were lost after a structural change:

```bash
python -c "import sys; sys.path.insert(0, '.'); from backend.main import app; print(sum(len(m) for m in app.openapi()['paths'].values()))"
```

This should print **37**.

Conventions for new code:

- All SQL is parameterised with `%s`. Never f-strings or string concatenation.
- Writes use `try / commit / except: rollback, raise / finally: cursor.close()`.
  Reads use `try / finally: cursor.close()`.
- Static routes must be declared **before** dynamic ones, or FastAPI matches the wrong
  route — `/students/me` comes before `/students/{student_id}`.
- Imports are absolute from the package root: `from backend.services import student_service`.
- Response models are per-endpoint. Create a new schema rather than overloading one.
