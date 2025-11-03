"""FastAPI router setup."""

from fastapi import APIRouter

from app.api import routes_ingest, routes_query


api_router = APIRouter()
api_router.include_router(routes_ingest.router, tags=["ingest"])
api_router.include_router(routes_query.router, tags=["query"])
