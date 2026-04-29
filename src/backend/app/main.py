from fastapi import FastAPI
from app.models import models
from app.db.session import engine
from app.api.endpoints import user

# tạo bảng DB
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Autonomous Analyst Agent Platform",
    description="A platform for autonomous analyst agents...",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Autonomous Analyst Agent Platform!"}

# router
app.include_router(user.router, prefix="/users", tags=["Users"])