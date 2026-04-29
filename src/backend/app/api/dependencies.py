from app.db.session import SessionLocal

# dependency db
def get_db() :
    db = SessionLocal()
    try:
        yield db 
    finally:
        db.close() 