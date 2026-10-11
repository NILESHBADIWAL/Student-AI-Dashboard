import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from chat_controller import ChatController


logger = logging.getLogger("student_ai.api")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
# The first file found in the frontend folder is served at "/".
FRONTEND_FILES = ("dashboard_front.html", "student-ai-dashboard.html")

MAX_QUESTION_LENGTH = 1000


# --------------------------------------------------------------------------
# Chat controller (created once, retried on the next request if it fails)
# --------------------------------------------------------------------------

_chat_controller = None
_controller_lock = threading.Lock()


def get_chat_controller():
    """Return the shared ChatController, creating it on first use.

    If it cannot be created (for example the database is down), a RuntimeError
    is raised so /ask answers with a clear 503 message instead of the whole
    server failing to start. The next request tries again.
    """
    global _chat_controller

    if _chat_controller is None:
        with _controller_lock:
            if _chat_controller is None:
                try:
                    _chat_controller = ChatController()
                except Exception as error:
                    raise RuntimeError("Could not start the chat controller.") from error
    return _chat_controller


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Warm up at startup so the first student does not wait for it.
    try:
        get_chat_controller()
    except RuntimeError:
        logger.exception("Chat controller failed to start. It will retry on the next request.")
    yield


app = FastAPI(title="Student AI Dashboard API", lifespan=lifespan)


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_LENGTH)


class Source(BaseModel):
    category: str
    title: str
    source: str


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


# --------------------------------------------------------------------------
# Error handling
# The frontend shows `detail` as a plain string, so every error returns
# JSON in the form {"detail": "<message>"}.
# --------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError):
    message = "Please enter a question."
    for error in exc.errors():
        error_type = str(error.get("type", ""))
        if "too_long" in error_type or "max_length" in error_type:
            message = f"Please keep your question under {MAX_QUESTION_LENGTH} characters."
            break
    return JSONResponse(status_code=422, content={"detail": message})


@app.exception_handler(Exception)
async def unexpected_error_handler(_request: Request, exc: Exception):
    logger.exception("Unexpected error while handling a request", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong while answering. Please try again."},
    )


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

def _find_frontend_file():
    for name in FRONTEND_FILES:
        path = FRONTEND_DIR / name
        if path.is_file():
            return path
    return None


@app.get("/", include_in_schema=False)
def dashboard():
    frontend_file = _find_frontend_file()
    if frontend_file is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dashboard file not found. Put {FRONTEND_FILES[0]} in {FRONTEND_DIR}.",
        )
    return FileResponse(
        frontend_file,
        media_type="text/html",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Please enter a question.")

    try:
        return get_chat_controller().ask(question)
    except RuntimeError as error:
        logger.exception("The chatbot database could not be used")
        raise HTTPException(
            status_code=503,
            detail="The chatbot database is currently unavailable.",
        ) from error