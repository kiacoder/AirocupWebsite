# AirocupWebsite

AirocupWebsite is a Flask-based registration and administration portal for managing teams, members, and payments for the Airocup competition. The project bundles the web server, database models, and admin/client workflows into a single deployable package.

## Features
- User registration with phone and email verification flags.
- Team management with dual-league selection, education-level checks, and automatic member statistics.
- Payment tracking with receipt uploads, payer metadata, and admin review (approve/reject/update status).
- Admin dashboards for clients, teams, news, chat, and payment oversight.
- Robust archiving and restoration flows for clients, teams, and members.
- Enhanced admin search with status filters and sortable results across clients, teams, and payments.

## Project Structure
- `src/python/app.py` – Flask application factory, HTTP routes, and CLI helpers.
- `src/python/admin.py` – Admin blueprint: dashboards, search, archiving, restoration, and payment/news management.
- `src/python/client.py` – Client-facing routes (team creation, member uploads, chats, etc.).
- `src/python/models.py` – SQLAlchemy models and enums for all persisted entities.
- `src/python/database.py` – Database engine setup, schema migration helpers, and validation utilities.
- `src/templates/` – Jinja templates for admin, client, and global views.
- `static/` & `Static/` – CSS, JS, and static assets served by Flask.

## Getting Started

### Prerequisites
- Python 3.10+
- `pip` and `virtualenv`

### Installation
1. Clone the repository and move into the project directory.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r src/python/requirements.txt
   ```
3. Create a `.env` file in the repository root with at least the following keys (see `src/python/config.py` for full list):
   ```env
   secret_key="<random secret>"
   admin_password_hash="<bcrypt hash of admin password>"
   flask_debug=true  # optional
   host=0.0.0.0
   port=5000
   ```

### Running the Server
- **Development**: 
  ```bash
  python -m src.python.app
  ```
  The server starts on `http://0.0.0.0:5000` by default. When `flask_debug` is true, Socket.IO runs in debug mode.

- **Database bootstrap**: Initialize core tables and seed geography/league data (also runs automatically on app start):
  ```bash
  flask --app src.python.app init-db
  ```

### Tests
No automated test suite is bundled. Run `python -m compileall src/python` to sanity-check syntax if desired.

## Database Overview
The application uses SQLite via SQLAlchemy. A quick reference for the core tables, important columns, and performance-related indexes is below.

- **clients**
  - Columns: `phone_number` (unique), `email` (unique), `password`, `registration_date`, `status` (`active`/`inactive`/`withdrawn`), phone verification fields.
  - Relationships: one-to-many with `teams`, `payments`, `history_logs`, `chat_messages`, `team_documents`.
  - Indexes: `(status, email)` and `(phone_number, status)` accelerate filtered admin searches.

- **teams**
  - Columns: `team_name` (unique), `client_id`, `league_one_id`, `league_two_id`, `education_level`, `team_registration_date`, `average_age`, `average_provinces`, `unpaid_members_count`, `status` (`active`/`inactive`/`withdrawn`).
  - Relationships: belongs to one `client` and two optional `league` rows; has many `members`, `payments`, and `team_documents`.
  - Indexes: `(client_id, status)` for archive filters; `(status, team_registration_date)` for chronological sorting.

- **members**
  - Columns: `name`, `birth_date`, `national_id`, `role` (`leader`, `coach`, `member`), `status`, `city_id`, `team_id`.
  - Constraints: `one_leader_per_team_idx` enforces a single leader per team.
  - Indexes: `(team_id, status)` keeps archived/active member lookups fast when toggling client/team visibility.

- **payments**
  - Columns: `team_id`, `client_id`, `amount`, `members_paid_for`, `receipt_filename`, optional `tracking_number`, `payer_name`, `payer_phone`, `paid_at`, `upload_date`, `status` (`pending`, `approved`, `rejected`).
  - Indexes: `(status, upload_date)` accelerates dashboard queues; `(team_id, status)` keeps per-team payment history queries quick.

- **provinces / cities**
  - Seed data used to populate forms. `members.city_id` references `cities.city_id`, and `cities.province_id` references `provinces.province_id`.

- **leagues**
  - Configurable competition leagues with `name`, optional `icon`, and `description`. Two optional foreign keys on `teams` reference leagues.

- **news**
  - Title, HTML content, optional image and template path, and `publish_date` timestamp.

- **history_logs**
  - Tracks significant client/admin actions. Stores `action`, `timestamp`, `client_id`, and `admin_involved` flag for auditing.

- **login_attempts**
  - Captures IP-addressed success/failure attempts with timestamps for monitoring.

- **password_resets**
  - Password reset tokens with `identifier` (phone/email), `identifier_type`, `code`, and timestamp.

- **chat_messages**
  - Admin-client chat history with `sender`, message text, and timestamp.

- **team_documents**
  - Uploaded document metadata for each team/client.

### Archiving & Restoration
- Entity `status` enums allow soft-archiving (inactive/withdrawn) without deleting rows.
- Admin routes can archive teams/members/clients and restore them later. Archived teams retain payment history and can be reactivated from both the client detail view and the advanced search/teams list.
- When a client is archived or restored, the linked teams and members are updated together to keep dashboards and counts in sync.

### Schema Compatibility and Upgrades
- `database.ensure_schema_upgrades()` runs at startup to align older SQLite files with the current schema. It will:
  - Add missing columns (education level, unpaid member counts, payer metadata, verification flags, etc.).
  - Normalize null `status` fields to sensible defaults to avoid comparison errors.
  - Create helper indexes for status-aware filtering and sorting on clients, teams, members, and payments to keep the admin experience responsive even on legacy databases.
- You can safely drop in an older database file; the helper will patch it in place. If you want to inspect the resulting structure, run `sqlite3 src/database/database.db '.schema'` after the app starts.

## Admin Tips
- Use **جستجوی پیشرفته** (Advanced Search) to filter by client/team status, payment state, and sorting preferences. Restoration actions are available directly from the results when an entity is archived.
- In **مدیریت جامع تیم‌ها** (Manage Teams), filter by archive status or payment status to quickly find teams to restore or review.
- The **مدیریت کاربران** (Manage Clients) page now supports searching and filtering archived accounts with one-click restoration.

