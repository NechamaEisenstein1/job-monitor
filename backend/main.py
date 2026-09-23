"""FastAPI application. Run with:  uvicorn backend.main:app --reload"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api import account_routes, admin_routes, routes
from backend.bootstrap import build_email_sender, google_oauth
from backend.config.settings import PROJECT_ROOT, Settings, load_matching_config, load_sources_config
from backend.infrastructure.db.session import make_engine, make_session_factory
from backend.observability import configure_logging

FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    configure_logging(settings.log_level)

    app = FastAPI(title="Job Monitor", version="3.2")
    app.state.settings = settings
    app.state.cfg = load_matching_config(settings.config_dir)
    app.state.sender = build_email_sender(settings)
    app.state.google = google_oauth(settings)  # None unless GOOGLE_CLIENT_ID/SECRET are set
    app.state.session_factory = make_session_factory(make_engine(settings.database_url))
    app.state.sources = load_sources_config(settings.config_dir)
    # Only the Vite dev server (npm run dev) is a separate origin; production is same-origin.
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True,
                       allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type", "X-Requested-With"])
    app.include_router(account_routes.router)
    app.include_router(admin_routes.router)
    app.include_router(routes.router)

    # Serve the built dashboard (npm run build) from the same origin, if present.
    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            candidate = (FRONTEND_DIST / path).resolve()
            if path and candidate.is_file() and FRONTEND_DIST.resolve() in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(Path(FRONTEND_DIST / "index.html"))

    return app


app = create_app()
