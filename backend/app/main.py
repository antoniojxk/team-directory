from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.api import router
from app.config import get_settings

app = FastAPI(
    title="Team Directory API",
    version="1.0.0",
    description="Fictional people. Explicit permissions. Audited confidential reads. "
    "Use /api/auth/token to sign in; /api/auth/me shows your current permissions.",
)
app.include_router(router)


@app.middleware("http")
async def security_headers(request: Request, call_next: RequestResponseEndpoint) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    elif request.url.path not in {"/docs", "/redoc"}:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'"
        )
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # FastAPI's default includes submitted input and can echo private notes/passwords.
    errors = [
        {"field": ".".join(map(str, err["loc"])), "type": err["type"]} for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Invalid input. Check required fields, allowed values and date order.",
            "errors": errors,
        },
    )


@app.exception_handler(IntegrityError)
async def conflict(request: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "detail": "This change conflicts with an existing or linked record. "
            "Check unique values and record constraints."
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    # Do not log SQL exception text: driver errors can contain confidential parameters.
    return JSONResponse(
        status_code=503,
        content={"detail": "The database is temporarily unavailable. Please try again."},
    )


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred."})


@app.get("/health", tags=["Operations"])
def health() -> dict[str, str]:
    """Process liveness only: does not wake the database or run migrations."""
    return {"status": "ok"}


static_dir = get_settings().static_dir.resolve()
if (static_dir / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str) -> FileResponse:
    # Allow only known frontend routes. API typos and missing assets stay JSON 404s.
    parts = path.strip("/").split("/")
    is_profile = len(parts) == 2 and parts[0] == "people" and parts[1].isdigit()
    if (
        path.strip("/") not in {"", "login", "people", "audit", "classifications"}
        and not is_profile
    ):
        raise HTTPException(404, "Route not found.")
    index = static_dir / "index.html"
    if not index.is_file():
        raise HTTPException(404, "Frontend build not found. Start Vite or build the frontend.")
    return FileResponse(index, headers={"Cache-Control": "no-cache"})
