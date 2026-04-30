from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.backend.app.models import models
from src.backend.app.schemas import schemas
from src.backend.app.db.session import SessionLocal
from src.backend.app.api.dependencies import get_db
from src.backend.app.schemas.schemas import Create_User, Login_User, Token, Message
from src.agents.supervisor_agent import chat_with_system


router = APIRouter() 


# send, receive message
@router.post("/send_message", response_model=Message, status_code=status.HTTP_200_OK)
def send_message(
    message : Message
) : 
    # Here you can implement logic to process the message, e.g., save to database, analyze, etc.
    # For demonstration, we will just return the received message.
    input_user_message = message.content
    response_message = chat_with_system(input_user_message)

    return {"content": response_message}