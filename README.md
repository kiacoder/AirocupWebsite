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
The application uses SQLite via SQLAlchemy. Core tables and relationships:

- **clients**: Registered accounts with `phone_number`, `email`, `password`, verification fields, and `status` (`active`/`inactive`/`withdrawn`). One-to-many with teams, payments, history logs, chat messages, and uploaded documents.
- **teams**: Owned by a client; track `team_name`, optional `league_one_id`/`league_two_id`, `education_level`, `average_age`, `average_provinces`, `unpaid_members_count`, and `status` (active or inactive/withdrawn). Related to members, payments, and team documents.
- **members**: Individual participants with `role` (`leader`, `coach`, `member`), `birth_date`, `national_id`, `city_id`, and `status`. Enforces a unique leader per team.
- **payments**: Receipt uploads with `amount`, `members_paid_for`, `receipt_filename`, optional `tracking_number`, `payer_name`, `payer_phone`, `paid_at`, and `status` (`pending`, `approved`, `rejected`). Linked to both a team and client.
- **provinces / cities**: Seed data for regional selection; members reference `cities` which reference `provinces`.
- **leagues**: Configurable competition leagues (id, name, icon, description) populated at startup.
- **news**: Articles with content, image, template path, and publish date.
- **history_logs**: Audit trail of client/admin actions with timestamps.
- **login_attempts**: Recorded login successes/failures with IP address metadata.
- **password_resets**: Password reset codes and timestamps.
- **chat_messages**: Admin-client chat history.
- **team_documents**: Uploaded documents per team/client with filenames and types.

### Archiving & Restoration
- Entity `status` enums allow soft-archiving (inactive/withdrawn) without deleting rows.
- Admin routes can archive teams/members/clients and restore them later. Archived teams retain payment history and can be reactivated from both the client detail view and the advanced search/teams list.

### Schema Compatibility
`database.ensure_schema_upgrades()` applies lightweight migrations on startup to add missing columns (education level, unpaid member counts, payer metadata, verification flags, etc.) and normalizes null statuses, making it safer to merge or reuse older SQLite files alongside the current codebase.

## Admin Tips
- Use **جستجوی پیشرفته** (Advanced Search) to filter by client/team status, payment state, and sorting preferences. Restoration actions are available directly from the results when an entity is archived.
- In **مدیریت جامع تیم‌ها** (Manage Teams), filter by archive status or payment status to quickly find teams to restore or review.
- The **مدیریت کاربران** (Manage Clients) page now supports searching and filtering archived accounts with one-click restoration.

