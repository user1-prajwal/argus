"""FastAPI application entrypoint for the ARGUS API layer.

See docs/api-model.md, "Purpose": this is the first ARGUS layer that
talks to the outside world. It contains no planning, routing, or
simulation logic -- see routes.py for every endpoint handler.
"""

from __future__ import annotations

from fastapi import FastAPI

from .routes import router

app = FastAPI(title="ARGUS API", version="1.0.0")
app.include_router(router)
