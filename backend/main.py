"""FastAPI application. Run with:  uvicorn backend.main:app --reload"""
from __future__ import annotations

from datetime import date

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from backend.api import account_routes, admin_routes, routes
from backend.api.seo import PageRenderer, classify, robots_txt, sitemap_xml
from backend.bootstrap import build_email_sender, google_oauth
from backend.config.settings import PROJECT_ROOT, Settings, load_matching_config, load_sources_config
from backend.infrastructure.db.session import make_engine, make_session_factory
from backend.observability import configure_logging

FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
SITE_UPDATED = date(2026, 9, 24)  # <lastmod> of the public pages; bump when their content changes

# Same-origin app: scripts/styles/API all come from our own host. Inline style attributes are
# used by the UI (bar widths), hence 'unsafe-inline' for styles only.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; "
    "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    configure_logging(settings.log_level)

    app = FastAPI(title="Job Monitor", version="3.3")
    app.state.settings = settings
    app.state.cfg = load_matching_config(settings.config_dir)
    app.state.sender = build_email_sender(settings)
    app.state.google = google_oauth(settings)  # None unless GOOGLE_CLIENT_ID/SECRET are set
    app.state.session_factory = make_session_factory(make_engine(settings.database_url))
    app.state.sources = load_sources_config(settings.config_dir)

    if not settings.public_base_url.startswith("https://"):
        # Development only: the Vite dev server (npm run dev) is a separate origin.
        app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True,
                           allow_methods=["GET", "POST", "PUT", "DELETE"],
                           allow_headers=["Content-Type", "X-Requested-With"])

    @app.middleware("http")
    async def security_headers(request: Request, call_next):  # noqa: ANN001, ANN202
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        if settings.cookie_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")  # never cache personal data
            response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
        return response

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> JSONResponse:
        """Used by the hosting platform: the app is up and the database answers."""
        try:
            with app.state.session_factory() as session:
                session.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001
            return JSONResponse({"status": "db_unavailable"}, status_code=503)
        return JSONResponse({"status": "ok"})

    app.include_router(account_routes.router)
    app.include_router(admin_routes.router)
    app.include_router(routes.router)

    @app.get("/robots.txt", include_in_schema=False)
    def robots() -> PlainTextResponse:
        return PlainTextResponse(robots_txt(settings))

    @app.get("/sitemap.xml", include_in_schema=False)
    def sitemap() -> Response:
        return Response(sitemap_xml(settings, SITE_UPDATED), media_type="application/xml")

    # Serve the built dashboard (npm run build) from the same origin, if present.
    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")
        pages = PageRenderer(FRONTEND_DIST / "index.html", settings)

        @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
        def spa(path: str) -> Response:
            candidate = (FRONTEND_DIST / path).resolve()
            if path and candidate.is_file() and FRONTEND_DIST.resolve() in candidate.parents:
                return FileResponse(candidate)  # favicon.svg etc.
            kind = classify("/" + path)
            # Unknown paths are real 404s (the app shows its own "not found"), never soft-404s.
            response = HTMLResponse(pages.render("/" + path), status_code=404 if kind == "unknown" else 200)
            if kind != "public":
                response.headers["X-Robots-Tag"] = "noindex, nofollow"
            return response

    return app


app = create_app()
