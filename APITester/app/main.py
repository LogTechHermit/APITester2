from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, engine as default_engine
from app.routers import customer_csv, customers

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"
IMPORT_FILE = STATIC_DIR / "import.html"


def create_app(database_engine: Engine = default_engine) -> FastAPI:
    session_factory = sessionmaker(bind=database_engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        Base.metadata.create_all(bind=database_engine)
        yield

    app = FastAPI(
        title="Customer API",
        description="A simple customer list with CRUD endpoints.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.session_factory = session_factory
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def customer_list_page() -> FileResponse:
        return FileResponse(INDEX_FILE, headers={"Cache-Control": "no-store"})

    @app.get("/import", include_in_schema=False)
    def customer_import_page() -> FileResponse:
        return FileResponse(IMPORT_FILE)

    app.include_router(customer_csv.router)
    app.include_router(customers.router)
    return app


app = create_app()
