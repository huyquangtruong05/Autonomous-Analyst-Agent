from fastapi import FastAPI
from src.backend.app.models import models
from src.backend.app.db.session import engine
from src.backend.app.api.endpoints import user
from src.backend.app.api.endpoints import message
from fastapi.middleware.cors import CORSMiddleware


models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Autonomous Analyst Agent Platform",
    description="A platform for autonomous analyst agents...",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Welcome to Autonomous Analyst Agent Platform!"}

# router
app.include_router(user.router, prefix="/users", tags=["Users"])
app.include_router(message.router, prefix="/messages", tags=["Messages"])