<h1 align="center">Grand Azure</h1>

<p align="center">
  A hotel management system built with Django — public booking website and staff dashboard,<br>
  shipped as a single Docker container with PostgreSQL inside.
</p>

<p align="center">
  <img alt="Python 3.14" src="https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white">
  <img alt="Django 6.1" src="https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-included-4169E1?logo=postgresql&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-one%20container-2496ED?logo=docker&logoColor=white">
</p>

---

## Overview

The system has two halves that share the same booking rules:

- **Public website** — guests browse rooms, check live availability, book without an account (pay at the hotel), and look up or cancel a booking with their reference and email.
- **Staff dashboard** — role-based screens for reservations, check-in and check-out, the room board, housekeeping, restaurant orders and the menu, invoices, staff accounts and shifts, and reports.

**Contents:** [Quick start](#quick-start) · [Features](#features) · [Tech stack](#tech-stack) · [Configuration](#configuration) · [Project structure](#project-structure) · [Design notes](#design-notes)

## Quick start

**You only need [Docker](https://docs.docker.com/get-docker/)** (Docker Desktop on Windows/macOS, or Docker Engine with the Compose plugin on Linux). Nothing else — no Python, Node or database to install.

```bash
git clone https://github.com/XooTB/hotel-management.git
cd hotel-management
docker compose up
```

That's it. The first run takes a few minutes while Docker builds the image, creates the PostgreSQL database and loads demo data. **Wait for this message in the terminal:**

```
  ================================================================
    Grand Azure Hotel is ready!

    Website:      http://localhost:8000
    Staff login:  http://localhost:8000/accounts/login/
    Username:     manager      Password: demo12345
  ================================================================
```

Then open **<http://localhost:8000>** in your browser.

### Demo logins

Every account uses the password **`demo12345`**. Each role sees a different part of the staff dashboard.

| Username | Role | Can use |
|---|---|---|
| `manager` | Manager | Everything, including reports, room types and staff |
| `reception` | Receptionist | Reservations, check-in/out, rooms, housekeeping, restaurant, billing |
| `housekeeping` | Housekeeping | Room board and housekeeping tasks |
| `restaurant` | Restaurant | Order board and menu |

Guests don't need an account: book a room from the website, then use the booking reference under **Manage booking**.

### Everyday commands

| To… | Run |
|---|---|
| Stop | Press `Ctrl+C` in the terminal |
| Start again (data kept) | `docker compose up` |
| Start over with fresh demo data | `docker compose down -v`, then `docker compose up` |
| Use another port if 8000 is taken | `HOTEL_PORT=8080 docker compose up`, then open <http://localhost:8080> |

## Features

| Area | What it does |
|---|---|
| Public site | Home, room list and details, availability search (HTMX), booking form, confirmation email with booking reference, manage and cancel a booking |
| Reservations | Search and filter (arrivals, departures, in-house), walk-in and phone bookings with a live availability panel, check-in with room picker, check-out, cancel, no-show |
| Rooms | Room board grouped by floor with inline status changes; managers edit rooms and room types (rates, capacity, amenities, photo) |
| Housekeeping | Tasks (cleaning, inspection, maintenance) with priority and assignee. Check-out creates a cleaning task automatically; finishing all tasks frees the room |
| Restaurant | Menu with dish photos, order screen with live totals, a kitchen board that refreshes itself, dine-in and room-service orders, charge to room, menu availability toggles |
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
- **Frontend:** server-rendered Django templates, **HTMX** (partial page updates), **Alpine.js** (small interactions), **Tailwind CSS v4**, **Chart.js**
- **Styling:** Tailwind is compiled ahead of time into `static/css/app.css`, which is committed and served by Django, so a page is styled on first paint and the CSS does not depend on a CDN. The scripts load from the jsDelivr CDN, pinned to exact versions with integrity hashes. Running or deploying the app needs no build step; only editing styles does (`scripts/build-css.sh`)
- **Serving:** Gunicorn. Every request goes through Django, which also serves the site photos in `static/img/` and uploaded photos (no `collectstatic` step)
- **Photos:** from Unsplash (free licence), see `static/img/CREDITS.md`. The demo seed attaches them to the room types and menu items; managers can replace any of them from the dashboard
- **Container:** Debian `python:3.14-slim-trixie`, PostgreSQL from Debian, `tini` as PID 1

### What happens inside the container

PostgreSQL and the Django app run in the same container. On start, `docker/entrypoint.sh`:

1. creates the PostgreSQL cluster in `/var/lib/hotel/postgres` (first start only),
2. starts PostgreSQL, listening on localhost inside the container only,
3. creates the database role and database if they're missing,
4. generates and saves a Django secret key unless one is provided,
5. runs migrations and loads demo data (skipped if the data is already there),
6. starts Gunicorn as a non-root user.

On `docker stop` it shuts down Gunicorn and then PostgreSQL cleanly. Everything that needs to persist (database, uploaded photos, secret key) lives in the single `/var/lib/hotel` volume.

## Configuration

All settings are environment variables — set them in `docker-compose.yml` or on the host.

| Variable | Default | Purpose |
|---|---|---|
| `DEMO_DATA` | `1` | Load demo data on first start (`0` to disable) |
| `DJANGO_SECRET_KEY` | generated | Set explicitly in real deployments |
| `DJANGO_ALLOWED_HOSTS` | `*` | Comma-separated host names |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | – | e.g. `https://hotel.example.com` when behind HTTPS |
| `DJANGO_SECURE_COOKIES` | `0` | `1` to mark session/CSRF cookies secure (HTTPS deployments) |
| `DJANGO_BEHIND_PROXY` | `0` | `1` when a reverse proxy terminates TLS (nginx, Caddy, Traefik) |
| `DJANGO_SUPERUSER_USERNAME` / `_PASSWORD` / `_EMAIL` | – | Create an extra manager (superuser) account on start |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | `hotel` | Internal database credentials |
| `GUNICORN_WORKERS` | `3` | Worker processes |
| `TIME_ZONE` | `UTC` | Hotel time zone, e.g. `Asia/Kolkata` |
| `HOTEL_NAME`, `HOTEL_CURRENCY`, `HOTEL_TAX_RATE` | Grand Azure Hotel, `$`, `10` | Branding and tax (%) |

### Running it for real

The container is self-contained, so a real deployment is the same image with a few variables set:

- Put it behind a reverse proxy that terminates TLS, and set `DJANGO_BEHIND_PROXY=1`, `DJANGO_SECURE_COOKIES=1`, `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`.
- Set `DJANGO_SECRET_KEY` yourself instead of relying on the generated one, and `DEMO_DATA=0` for a clean database.
- Keep **one container per volume** — the database lives inside it, so a second replica would start a second, empty database.
- Back up with `pg_dump`:
  ```bash
  docker compose exec hotel runuser -u postgres -- pg_dump -h /var/run/postgresql hotel > backup.sql
  ```

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
assets/app.css          Tailwind source: theme colours, custom utilities, component classes
static/css/app.css      compiled stylesheet (committed; regenerate with scripts/build-css.sh)
scripts/build-css.sh    rebuilds static/css/app.css from assets/app.css
docker/entrypoint.sh    starts PostgreSQL and Gunicorn in the container
scripts/wait-healthy.sh waits for the container health check (used by CI)
.github/workflows/      CI: tests on PostgreSQL + container smoke test
docs/diagrams.md        ER, use-case, class, sequence and state diagrams
```

## Design notes

- **Business rules live in `services.py` modules**, not in views, so the website, the dashboard and the tests all share the same logic.
- **Inventory is held per room type.** A specific room is assigned at check-in, which is how real hotels work. Availability is the number of bookable rooms minus the **busiest night** of the requested stay. Bookings lock the room type row (`SELECT … FOR UPDATE`) so two guests can't take the last room at the same moment.
- **Rates and prices are snapshotted.** The nightly rate is copied onto the reservation, and menu prices onto order lines, so later price changes don't rewrite history.
- **No guest accounts.** A guest proves ownership of a booking with its reference plus email, and access is remembered for the browser session.
