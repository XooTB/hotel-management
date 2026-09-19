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
- **Frontend:** server-rendered Django templates, **HTMX** (partial page updates), **Alpine.js** (small interactions), **Tailwind CSS v4** (browser build), **Chart.js**. All front-end libraries load from the jsDelivr CDN, pinned to exact versions with integrity hashes, so there is no build step
- **Serving:** Gunicorn. Every request goes through Django, which also serves the site photos in `static/img/` and uploaded photos (no `collectstatic` step)
- **Photos:** from Unsplash (free licence), see `static/img/CREDITS.md`. The demo seed attaches them to the room types and menu items; managers can replace any of them from the dashboard
- **Container:** Debian `python:3.14-slim-trixie`, PostgreSQL from Debian, `tini` as PID 1

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

### Stopping and starting again

| To… | Run |
|---|---|
| Stop | Press `Ctrl+C` in the terminal |
| Start again (data kept) | `docker compose up` |
| Start over with fresh demo data | `docker compose down -v` then `docker compose up` |
| Use another port if 8000 is taken | `HOTEL_PORT=8080 docker compose up`, then open <http://localhost:8080> |

### What happens inside the container

PostgreSQL and the Django app run in the same container. On start, `docker/entrypoint.sh`:

1. creates the PostgreSQL cluster in `/var/lib/hotel/postgres` (first start only),
2. starts PostgreSQL, listening on localhost inside the container only,
3. creates the database role and database if they're missing,
4. generates and saves a Django secret key unless one is provided,
5. runs migrations and loads demo data (skipped if the data is already there),
6. starts Gunicorn as a non-root user.

On `docker stop` it shuts down Gunicorn and then PostgreSQL cleanly. Everything that needs to persist (database, uploaded photos, secret key) lives in the single `/var/lib/hotel` volume.

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DEMO_DATA` | `1` | Load demo data on first start (`0` to disable) |
| `DJANGO_SECRET_KEY` | generated | Set explicitly in real deployments |
| `DJANGO_ALLOWED_HOSTS` | `*` | Comma-separated host names |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | – | e.g. `https://hotel.example.com` when behind HTTPS |
| `DJANGO_SECURE_COOKIES` | `0` | `1` to mark session/CSRF cookies secure (HTTPS deployments) |
| `DJANGO_BEHIND_PROXY` | `0` | `1` when a proxy terminates TLS (Fly.io, nginx) |
| `DJANGO_SUPERUSER_USERNAME` / `_PASSWORD` / `_EMAIL` | – | Create an extra manager (superuser) account on start |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | `hotel` | Internal database credentials |
| `GUNICORN_WORKERS` | `3` | Worker processes |
| `TIME_ZONE` | `UTC` | Hotel time zone, e.g. `Asia/Kolkata` |
| `HOTEL_NAME`, `HOTEL_CURRENCY`, `HOTEL_TAX_RATE` | Grand Azure Hotel, `$`, `10` | Branding and tax (%) |

## Deploying to Fly.io

The same image runs on Fly.io as one machine with a persistent volume — the app
and its PostgreSQL database stay together, exactly as in Docker Compose.
`fly.toml` is in the repo; you need [flyctl](https://fly.io/docs/flyctl/install/)
and a Fly account.

1. **Pick an app name.** In `fly.toml`, replace `hotel-management` in both `app`
   and `DJANGO_CSRF_TRUSTED_ORIGINS` with a name of your own (it must be unique
   across Fly), and set `primary_region` to the region closest to you
   (`fly platform regions` lists them).

2. **Create the app** (don't use `fly launch` — it detects Django and offers
   to provision a separate Fly Postgres database, which this setup doesn't use):

   ```bash
   fly apps create <your-app-name>
   ```

3. **Set the secret key** so it does not depend on the volume:

   ```bash
   fly secrets set DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
   ```

4. **Create the volume** (1 GB is plenty; use the same region as `primary_region`):

   ```bash
   fly volumes create hotel_data --size 1 --region <your-region>
   ```

5. **Deploy** — `--ha=false` keeps it to a single machine, which matters because
   the database lives inside it:

   ```bash
   fly deploy --ha=false
   ```

6. **Open the site:** `fly open`, then sign in at `/accounts/login/` with the
   demo logins above. To add your own manager account, set the superuser
   variables as secrets — the machine restarts and the entrypoint creates it:

   ```bash
   fly secrets set DJANGO_SUPERUSER_USERNAME=owner \
                   DJANGO_SUPERUSER_PASSWORD='<a strong password>' \
                   DJANGO_SUPERUSER_EMAIL=you@example.com
   ```

Useful afterwards: `fly logs`, `fly status`, `fly ssh console`, and
`fly deploy --ha=false` again after every `git push`.

### Notes on this setup

- **One machine only.** Each machine gets its own volume, so a second one would
  run a second, empty database. Keep `fly scale count 1` and always deploy with
  `--ha=false`.
- **No release command.** Migrations run from the container's entrypoint, since
  the database only exists inside the machine that mounts the volume.
- **Cold starts.** `min_machines_running = 0` lets Fly stop the machine when
  nobody is using it (cheaper); the first request afterwards waits a few seconds
  while PostgreSQL starts. Set it to `1` in `fly.toml` to keep the site warm.
- **Demo data** is loaded on the first boot only. Set `DEMO_DATA = '0'` in
  `fly.toml` for a clean production database.
- **Backups:** `fly ssh console -C "runuser -u postgres -- pg_dump -h /var/run/postgresql hotel" > backup.sql`,
  or snapshot the volume with `fly volumes snapshots create <volume-id>`.
- **Management commands** over SSH need the database URL, which only the
  entrypoint exports:
  `fly ssh console -C "env DATABASE_URL=postgres://hotel:hotel@127.0.0.1:5432/hotel /opt/venv/bin/python /app/manage.py <command>"`.

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
