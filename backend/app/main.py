from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.routes.health import router as health_router
from app.api.routes.observations import router as observations_router
from app.api.routes.tracklets import router as tracklets_router


app = FastAPI()
register_error_handlers(app)
app.include_router(health_router, prefix="/api")
app.include_router(observations_router, prefix="/api")
app.include_router(tracklets_router, prefix="/api")
