# Grand Azure — Hotel Management System

A hotel management system built with **Django**. It has two parts:

- **Public website:** guests browse rooms, check live availability, book without an account (pay at the hotel), and look up or cancel a booking with their booking reference and email.
- **Staff dashboard:** role-based screens for reservations, check-in and check-out, the room board, housekeeping, restaurant orders and the menu, invoices, staff accounts and shifts, and reports.

The whole application, **including PostgreSQL**, ships as **one Docker container**.

## Features

| Area | What it does |
|---|---|
| Public site | Home, room list and details, availability search (HTMX), booking form, confirmation email with booking reference, manage and cancel a booking |
| Reservations | Search and filter (arrivals, departures, in-house), walk-in and phone bookings with a live availability panel, check-in with room picker, check-out, cancel, no-show |
| Rooms | Room board grouped by floor with inline status changes; managers edit rooms and room types (rates, capacity, amenities, photo) |
| Housekeeping | Tasks (cleaning, inspection, maintenance) with priority and assignee. Check-out creates a cleaning task automatically; finishing all tasks frees the room |
| Restaurant | Order screen with live totals, a kitchen board that refreshes itself, dine-in and room-service orders, charge to room, menu availability toggles |
| Billing | Invoice created at check-out (room nights plus charges to the room, plus tax), printable invoice, mark as paid (cash or card) |
| Staff | Staff accounts with roles, weekly shift schedule with overlap checks |
| Reports | Occupancy, revenue collected, average daily rate, restaurant sales, bookings by room type and channel, top menu items (Chart.js) |

### Roles

| Role | Can use |
|---|---|
| Manager | Everything, including room types, staff, shifts and reports |
| Receptionist | Reservations, rooms, housekeeping, restaurant, billing |
| Housekeeping | Room board and housekeeping tasks |
| Restaurant | Order board and menu |

Everyone can see their own shifts.

## Tech stack

- **Backend:** Python 3.14, Django 6.1, PostgreSQL (SQLite for quick local development)
- **Frontend:** server-rendered Django templates, **HTMX** (partial page updates), **Alpine.js** (small interactions), **Tailwind CSS v4** (browser build), **Chart.js**. All front-end libraries load from the jsDelivr CDN, pinned to exact versions with integrity hashes, so there is no build step and no static files to serve
- **Serving:** Gunicorn. Every request goes through Django; the only files it serves are uploaded room photos
- **Container:** Debian `python:3.14-slim-trixie`, PostgreSQL from Debian, `tini` as PID 1

## Quick start (Docker)

The only requirement is Docker with Compose v2.

```bash
git clone <repository-url> hotel-management
cd hotel-management
docker compose up --build
```

The first start takes a few minutes while the image builds and the database is created. When the log shows `Starting Gunicorn`, open:

- **Website:** <http://localhost:8000>
- **Staff dashboard:** <http://localhost:8000/accounts/login/> (for example `manager` / `demo12345`; see [demo accounts](#demo-accounts))

| Task | Command |
|---|---|
| Run in the background | `docker compose up -d --build` |
| Follow the logs | `docker compose logs -f` |
| Stop (data is kept) | `docker compose down` |
| Reset to fresh demo data | `docker compose down -v && docker compose up --build` |
| Use another port if 8000 is taken | `HOTEL_PORT=8080 docker compose up --build` |

### What happens inside the container

PostgreSQL and the Django app run in the same container. On start, `docker/entrypoint.sh`:

1. creates the PostgreSQL cluster in `/var/lib/hotel/postgres` (first start only),
2. starts PostgreSQL, listening on localhost inside the container only,
3. creates the database role and database if they're missing,
4. generates and saves a Django secret key unless one is provided,
5. runs migrations and loads demo data (skipped if the data is already there),
6. starts Gunicorn as a non-root user.

On `docker stop` it shuts down Gunicorn and then PostgreSQL cleanly. Everything that needs to persist (database, uploaded photos, secret key) lives in the single `/var/lib/hotel` volume.

### Demo accounts

All demo accounts use the password **`demo12345`**.

| Username | Role |
|---|---|
| `admin` | Manager (superuser) |
| `manager` | Manager |
| `reception` | Receptionist |
| `housekeeping` | Housekeeping |
| `restaurant` | Restaurant |

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DEMO_DATA` | `1` | Load demo data on first start (`0` to disable) |
| `DJANGO_SECRET_KEY` | generated | Set explicitly in real deployments |
| `DJANGO_ALLOWED_HOSTS` | `*` | Comma-separated host names |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | – | e.g. `https://hotel.example.com` when behind HTTPS |
| `DJANGO_SUPERUSER_USERNAME` / `_PASSWORD` / `_EMAIL` | – | Create an extra manager (superuser) account on start |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | `hotel` | Internal database credentials |
| `GUNICORN_WORKERS` | `3` | Worker processes |
| `TIME_ZONE` | `UTC` | Hotel time zone, e.g. `Asia/Kolkata` |
| `HOTEL_NAME`, `HOTEL_CURRENCY`, `HOTEL_TAX_RATE` | Grand Azure Hotel, `$`, `10` | Branding and tax (%) |

## Local development

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py seed_demo            # --reset to reload
uv run python manage.py runserver
```

Local development uses SQLite by default. To use PostgreSQL, set `DATABASE_URL=postgres://user:pass@localhost:5432/hotel`.

## Tests

```bash
uv run python manage.py test
```

Every push to GitHub also runs the checks in `.github/workflows/ci.yml`: the test suite against a real PostgreSQL database, plus a build of the Docker image that starts the container, waits for its health check, requests the main pages and restarts it to confirm the data persists.

The tests cover:

- **Availability:** back-to-back stays, busiest night counted correctly, overbooking prevented, cancellations free up rooms, rooms under maintenance excluded
- **Validation:** stay rules and room capacity
- **Stay lifecycle:** check-in, then check-out, then invoice plus housekeeping task
- **Billing:** invoice totals and tax
- **Housekeeping:** rooms freed when tasks finish
- **Public booking:** booking, lookup and cancellation from the website
- **Permissions:** role-based access control

## Project structure

```
config/                 settings, root URLs, WSGI
apps/
  accounts/             staff User model (roles), login, permission helpers
  rooms/                RoomType, Room, Amenity; room board and management
  reservations/         Reservation model, booking rules (services.py), front-desk views
  billing/              Invoice, InvoiceLine; invoice generation and payment
  housekeeping/         HousekeepingTask; task board
  restaurant/           Menu, orders, kitchen board
  staff/                Shift schedule, staff management
  dashboard/            overview, reports, shared UI template tags, seed_demo command
  website/              public site and guest booking flow
templates/              all HTML templates (base, website, dashboard sections, partials)
templates/components/tailwind.html  Tailwind theme colours and component classes
docker/entrypoint.sh    starts PostgreSQL and Gunicorn in the container
scripts/wait-healthy.sh waits for the container health check (used by CI)
.github/workflows/      CI: tests on PostgreSQL + container smoke test
docs/diagrams.md        ER, use-case, class, sequence and state diagrams
```

### Design notes

- **Business rules live in `services.py` modules**, not in views, so the website, the dashboard and the tests all share the same logic.
- **Inventory is held per room type.** A specific room is assigned at check-in, which is how real hotels work. Availability is the number of bookable rooms minus the **busiest night** of the requested stay. Bookings lock the room type row (`SELECT … FOR UPDATE`) so two guests can't take the last room at the same moment.
- **Rates and prices are snapshotted.** The nightly rate is copied onto the reservation, and menu prices onto order lines, so later price changes don't rewrite history.
- **No guest accounts.** A guest proves ownership of a booking with its reference plus email, and access is remembered for the browser session.
