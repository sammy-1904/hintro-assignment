# Testing Guide

This document describes how our test suite is structured, the scenarios covered, and how to verify everything locally.



## How to Run the Tests

To keep tests fast and easy to run, we use an **in-memory SQLite database** (`aiosqlite`). You do not need to have PostgreSQL running to run the test suite. 

In `tests/conftest.py`, we override the FastAPI database dependency (`get_db`) to inject a clean SQLite connection for every test run.

### Running the Suite
Make sure you have installed the testing dependencies, then run:
```bash
python -m pytest -v
```



## What We Tested

Our unit tests cover 23 different test cases across three main areas:

### 1. Authentication (`tests/test_auth.py`)
* **Registering**: Checks successful registration, invalid/malformed email rejection, and passwords that are too short.
* **Duplicates**: Verifies that registering with an email that already exists returns a `409` conflict error.
* **Logging In**: Tests successful login (returns JWT token), bad password rejection, and non-existent user handling.
* **Route Protection**: Ensures endpoints requiring auth return `401 Unauthorized` if no valid token is provided.
* **Health Check**: Verifies `/health` returns `200` status.

### 2. Meeting Management (`tests/test_meetings.py`)
* **Creation**: Tests creating a meeting with valid transcripts, and validates errors for missing fields (like an empty title or empty transcript list).
* **Retrieval**: Verifies you can fetch a specific meeting by ID and receive a `404` for missing IDs.
* **Pagination**: Tests that meeting lists are paginated correctly.
* **Privacy/Isolation**: Verifies that User A cannot see or list meetings belonging to User B.

### 3. Action Items (`tests/test_action_items.py`)
* **Creation & Schema**: Validates action item structure, including linking to meetings and storing citations.
* **Status Updates**: Tests transitions between statuses (e.g., `PENDING` -> `IN_PROGRESS` -> `COMPLETED`) and rejects invalid statuses.
* **Overdue Filtering**: Verifies the query returns items that are past due and not completed, while excluding items that are past due but already marked as `COMPLETED`.



## Edge Cases Handled

* **Email Enumeration Defense**: The login endpoint returns the exact same error message (`INVALID_CREDENTIALS`) whether the email doesn't exist or the password is wrong. This prevents attackers from scanning for valid emails.
* ** फास्टAPI Path Order**: The `/api/action-items/overdue` endpoint is placed above generic item endpoints in the router. If it were below, FastAPI would match `"overdue"` as a path variable (`item_id`) and fail.
* **Cross-User Leak Prevention**: All DB queries for meetings and action items explicitly check `where(User.id == current_user.id)` to guarantee database-level isolation between accounts.



## Testing Limitations & Manual Steps

1. **SQLite vs PostgreSQL**: SQLite does not support PostgreSQL's `JSONB` type. In SQLite, it falls back to a text-based JSON column. While this works perfectly for standard CRUD tests, PostgreSQL-specific operations (like JSON sub-query indexing) can only be verified on the production DB.
2. **AI & Email Mocking**: We do not call the live Gemini API or Resend API inside unit tests to avoid using up rate limits and depending on external services during tests. Instead:
   * **Gemini** and **Resend** integrations were tested manually.
   * You can test Resend manually by creating an action item assigned to your Resend registration email, setting the due date in the past, and calling the `/api/action-items/trigger-reminders` endpoint to trigger an email send.
