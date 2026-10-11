# Student AI Dashboard API

From the project root, create a virtual environment and install the backend
dependencies:

```powershell
Copy-Item .env.example .env
# Set DB_PASSWORD in .env to your local MySQL password.
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

To start the dashboard on Windows, double-click `run_dashboard.bat` in the
project root, then open <http://localhost:8000/>. Keep the terminal window open
while using the dashboard; press Ctrl+C in it to stop the server. Do not open
`frontend/dashboard_front.html` directly, because the chat needs to be served
by the API.

Alternatively, run the server from PowerShell in the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api:app --app-dir backend --host 127.0.0.1 --port 8000
```

The API documentation is available at <http://localhost:8000/docs>.

Database settings are loaded from the project-root `.env` file. It is excluded
from version control; keep database credentials there rather than in source
files. `.env.example` documents the required settings without containing
credentials.

`POST /ask` accepts `{"question": "..."}` and returns an `answer` and a list
of `sources`. The chatbot searches the configured MySQL database's public
information tables (attendance rules, fees, notices, past questions, courses,
exam/library/hostel rules, FAQs, scholarships, and the academic calendar).
It does not query individual student attendance or student records. MySQL must
be running and these tables must be populated for relevant answers.
