from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from APP import config
from APP.routes import router

app = FastAPI(title="ComicCraft")

app.mount(
    "/static",
    StaticFiles(directory=str(config.STATIC_DIR)),
    name="static"
)

app.include_router(router)