# Technical Decisions

Here is a quick breakdown of why we chose the tools and architecture we did for the Hintro project, including the alternatives we considered and the trade-offs we accepted.



## 1. Web Framework: FastAPI
We went with **FastAPI** over Flask or Django.
* **Why**: It is built from the ground up for modern asynchronous Python. Since we are doing non-blocking DB calls and API calls to Gemini and Resend, `async/await` is critical. It also autogenerates OpenAPI/Swagger docs from our type hints without any extra configuration.
* **Alternatives**: Flask (a bit too bare-bones and synchronous by default) and Django REST Framework (overkill and too heavy for a simple microservice).
* **Trade-off**: Writing asynchronous Python code requires using async drivers and being careful not to run blocking sync code in routers.



## 2. Database: PostgreSQL & SQLAlchemy (Async)
We chose **PostgreSQL** coupled with **SQLAlchemy** (using the `asyncpg` driver).
* **Why**: The project needs to store structured transcripts, AI analyses, and citation arrays. PostgreSQL's `JSONB` column type is perfect for this—it gives us the flexibility of a document store while retaining full relational constraints for tables like `users` and `action_items`.
* **Alternatives**: MongoDB (schemaless, but relational integrity for users/tasks makes a SQL DB a safer choice) or SQLite (fine for local testing, but not robust enough for concurrent production environments).
* **Trade-off**: Since `JSONB` is PostgreSQL-specific, we had to write a fallback database-agnostic type in `app/database.py` so unit tests can run against an in-memory SQLite database.



## 3. Authentication: JSON Web Tokens (JWT)
We implemented stateless **JWT Authentication** (HS256).
* **Why**: It's stateless and doesn't require session storage on the server, meaning it scales horizontally. It's also incredibly easy for evaluators to test using Postman or Swagger's built-in "Authorize" button.
* **Alternatives**: Session-based auth (requires setting up Redis or a sessions table in the DB, adding infrastructure overhead) or OAuth2/third-party login (adds third-party dependency complexity).
* **Trade-off**: You cannot easily revoke a JWT once it has been issued unless you implement a blacklist or short expiry times. For this assignment, we set the token lifetime to 24 hours.



## 4. AI Provider: Google Gemini
We used **Google Gemini** (specifically `gemini-3.5-flash`).
* **Why**: It is extremely fast, free to use under developer rate limits, and does a great job returning structured JSON. It also has a native async SDK, which integrates perfectly with FastAPI.
* **Alternatives**: OpenAI GPT-4o (more expensive, requires setting up billing) or Llama/Groq (fast, but less reliable at following complex JSON schemas in our tests).
* **Trade-off**: Gemini sometimes appends markdown formatting backticks around its JSON output. We handle this with a simple utility function that strips the backticks before parsing.



## 5. Email Integration: Resend
For sending overdue notifications, we integrated **Resend**.
* **Why**: It has a simple Python SDK, a straightforward REST API (no complex SMTP config needed), and a generous free tier (100 emails/day).
* **Alternatives**: SendGrid (excellent, but the API is more verbose) or webhooks like Slack/Discord (harder to test without setting up dedicated channels).
* **Trade-off**: The Resend free tier restricts sending emails to only the account owner's registered email address. Additionally, you must send emails from `onboarding@resend.dev` unless you verify a custom domain. We configured our `.env` to respect these rules.



## 6. Background Task Scheduler: APScheduler
We used **APScheduler** (`AsyncIOScheduler`) to run the overdue reminder checks.
* **Why**: It runs directly inside the FastAPI process on the existing asyncio event loop. It does not require setting up a separate background worker or message queue.
* **Alternatives**: Celery + Redis (the industry standard for background jobs, but requires running Redis and a separate Celery process, which is overengineered for this assignment).
* **Trade-off**: Because it runs in-process, if the server restarts, any scheduled tasks stop executing until the server boots back up. Also, if we scale the API to multiple containers, they would all run the scheduler independently, potentially sending duplicate emails. (For a production system, we would migrate to Celery/Redis).



## 7. Folder Structure: Layered Architecture
The project is split into folders by concern:
* `app/routers/`: HTTP endpoints and request routing.
* `app/services/`: Core business logic (AI prompt runs, Resend email logic, scheduler configuration).
* `app/models/`: SQLAlchemy database models.
* `app/schemas/`: Pydantic validation schemas.
* `app/utils/`: Middleware, custom error classes, and responses.

* **Why**: Keeps routers lightweight, keeps code highly organized, and makes writing unit tests for specific modules very simple.
