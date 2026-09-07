from fastapi import FastAPI, status
from contextlib import asynccontextmanager
from app.db import connect_to_mongo, close_mongo_connection
from app.errors import ApiError
from app.error_handlers import api_error_handler
from app.routers import jogos

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(title="API de Jogos", lifespan=lifespan)

app.add_exception_handler(ApiError, api_error_handler)

app.include_router(jogos.router)

@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    return {"mensagem": "API de Jogos funcionando"}