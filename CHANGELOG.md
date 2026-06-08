# Changelog

All notable changes and development milestones for the Hintro Meeting Intelligence backend are recorded here.




### 1. Foundation & Infrastructure
* Set up the FastAPI framework structure.
* Integrated asynchronous database support using PostgreSQL, SQLAlchemy, and `asyncpg` connection pooling.
* Created a database-agnostic JSON column handler so tests can run cleanly on SQLite.
* Configured structured JSON logging.
* Added standard API response envelope middleware (`{"traceId", "success", "data"}`).
* Configured Dockerfile and Docker Compose configurations.

### 2. User Authentication
* Created the User DB model with encrypted passwords (via standard bcrypt).
* Implemented secure token-based logins (`POST /api/auth/register` and `POST /api/auth/login`).
* Added JWT decoding dependency middleware to protect secure endpoints.

### 3. Meetings CRUD & AI Analysis
* Designed the Meeting model with flexible JSON fields for participants and transcripts.
* Added meeting creation and details endpoints.
* Built AI analysis integration using Google Gemini (`gemini-3.5-flash`).
* Designed prompt grounding instructions to force Gemini to output citations for all insights.
* Created a backend post-processing validator that removes any hallucinated timestamps.

### 4. Action Items & Overdue Logic
* Designed the ActionItem model tracking status (`PENDING`, `IN_PROGRESS`, `COMPLETED`), assignee, and due dates.
* Implemented endpoints to update task status and search for overdue items.
* Excluded completed items from overdue notifications even if their due dates are in the past.

### 5. Email Reminders Integration
* Integrated the Resend Python SDK for transactional email reminders.
* Configured a background job runner using `AsyncIOScheduler` (APScheduler) running directly in the FastAPI event loop.
* Set up a manual override endpoint (`POST /api/action-items/trigger-reminders`) for easy evaluator testing.
* Added a database audit log (`ReminderHistory`) to record the status of every notification attempt.
