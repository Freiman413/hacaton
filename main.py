
import uvicorn
import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from dotenv import load_dotenv
from router import pages
from router import lecturer_dashboard
from router import admin
from data_base.db import init_database
from ai_server import main_server

load_dotenv()
init_database()
app = FastAPI()
APP_NAME = os.environ["APP_NAME"]
HOST = os.environ["HOST"]
PORT = int(os.environ["PORT"])
DEBUG_MODE = os.environ["DEBUG"].lower() == "true"
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

app.include_router(pages.router)
app.include_router(lecturer_dashboard.router)
app.include_router(admin.router)
app.include_router(main_server.router)

if __name__ == "__main__":
    uvicorn.run(app=APP_NAME, host=HOST, port=PORT, reload=DEBUG_MODE)
    