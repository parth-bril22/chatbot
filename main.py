import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from routes.api import router as api_router
from fastapi_sqlalchemy import DBSessionMiddleware
from src.dependencies.config import API_PREFIX, DATABASE_URL, API_PREFIX

app = FastAPI()
app.add_middleware(DBSessionMiddleware, db_url=DATABASE_URL)
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.include_router(api_router)
app.include_router(api_router, prefix=API_PREFIX)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info", reload=True)
