# Hintro Meeting Intelligence Service

This is an AI-powered FastAPI backend service that manages meetings, extracts grounded summaries and action items from transcripts using Google Gemini, and sends email reminders for overdue tasks via Resend.



## Technical Stack
* **Framework**: FastAPI (Python 3.12+)
* **Database**: PostgreSQL (with asyncpg + SQLAlchemy)
* **AI Engine**: Google Gemini (using the `gemini-3.5-flash` model)
* **Email Service**: Resend
* **Job Scheduler**: APScheduler (AsyncIOScheduler)



## Features
* **JWT Authentication**: User registration and login endpoints.
* **Meeting Management**: Create and list meetings along with their raw speaker transcripts.
* **AI analysis**: Extract meeting summaries, decisions, follow-ups, and action items.
* **Citations & Grounding**: Every AI insight references the exact timestamp from the transcript to prevent hallucinations.
* **Overdue Detection**: Find tasks that are past due.
* **Automated Email Reminders**: Scans for overdue items and emails assignee notifications.
* **Robust Structure**: Structured JSON logging, custom exception handling, and standard envelope responses (`{"traceId", "success", "data"}`).



## Local Setup

### Prerequisites
* Python 3.12+
* PostgreSQL running locally
* A Google Gemini API key
* A Resend API key

### 1. Clone & Navigate
```bash
git clone https://github.com/sammy-1904/hintro-assignment.git
cd hintro-assignment
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in the values in `.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/hintro
SECRET_KEY=generate_with_python_secrets
GEMINI_API_KEY=your-gemini-api-key
RESEND_API_KEY=your-resend-api-key
REMINDER_FROM_EMAIL=onboarding@resend.dev
```
> [!IMPORTANT]
> If you are using a free Resend developer/sandbox account, you must set `REMINDER_FROM_EMAIL=onboarding@resend.dev`. Resend sandbox accounts only allow sending emails to the email address registered on the Resend account itself.

### 5. Initialize Database
Create your local PostgreSQL database:
```sql
CREATE DATABASE hintro;
```

### 6. Run the Application
Start the Uvicorn server:
```bash
uvicorn app.main:app --reload
```
* The API runs locally at: `http://localhost:8000`
* Interactive API Documentation (Swagger) is available at: `http://localhost:8000/docs`



## Running Unit Tests
To run the automated tests (uses an isolated in-memory SQLite database):
```bash
pip install aiosqlite
python -m pytest -v
```



## Docker Setup
You can spin up the application along with a PostgreSQL database using Docker Compose:
1. Ensure your `.env` contains your API keys.
2. Run:
   ```bash
   docker-compose up --build
   ```
The app will be accessible at `http://localhost:8000`.



## API Examples

### 1. Register a User
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "your_email@example.com", "password": "secure_password_123"}'
```

### 2. Login & Get Token
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your_email@example.com", "password": "secure_password_123"}'
```

### 3. Create a Meeting with a Transcript
```bash
curl -X POST http://localhost:8000/api/meetings \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Project Sync",
    "participants": ["your_email@example.com"],
    "meetingDate": "2026-06-08T10:00:00Z",
    "transcript": [
      {"timestamp": "00:10", "speaker": "Alex", "text": "We need to fix the database index before Wednesday."},
      {"timestamp": "00:45", "speaker": "Jordan", "text": "I will handle the index configuration change."}
    ]
  }'
```

### 4. Analyze Meeting (AI Insights)
```bash
curl -X POST http://localhost:8000/api/meetings/<meeting-id>/analyze \
  -H "Authorization: Bearer <your_jwt_token>"
```

### 5. Manually Trigger Email Reminders
To check and trigger overdue email notifications immediately without waiting for the scheduler interval:
```bash
curl -X POST http://localhost:8000/api/action-items/trigger-reminders \
  -H "Authorization: Bearer <your_jwt_token>"
```
