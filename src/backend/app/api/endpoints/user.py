from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models import models
from app.schemas import schemas
from app.db.session import SessionLocal
from app.api.dependencies import get_db
from app.schemas.schemas import Create_User, Login_User, Token


# auth
from app.auth.auth import hash_password, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm 
from jose import JWTError, jwt


router = APIRouter() 

# create user
@router.post("/register", response_model=schemas.Create_User, status_code=status.HTTP_201_CREATED)
def create_user(
    user:Create_User,
    db:Session = Depends(get_db)
) : 
    get_user_from_db = db.query(models.User).filter(models.User.username==user.username or models.User.email==user.email).first()
    if get_user_from_db :
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    else :
        new_user = models.User(username=user.username, email=user.email, password=hash_password(user.password))
        db.add(new_user)
        db.commit()
        db.refresh(new_user) 
        return new_user
    
# login user :
@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK) 
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db:Session=Depends(get_db)
) : 
    get_user_from_db = db.query(models.User).filter(models.User.username == form_data.username).first()

    if not get_user_from_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    if not verify_password(form_data.password, get_user_from_db.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    access_token = create_access_token({
        "sub": get_user_from_db.username
    })

    return {"access_token": access_token, "token_type": "bearer"}

# auth router
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")
def get_current_user(token : str = Depends(oauth2_scheme)) : 
    try : 
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username : str = payload.get("sub")
        if username is None :
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
        return username
    
    except JWTError :
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
@router.get("/me")
def read_users_me(current_user: str = Depends(get_current_user)) : 
    return {"username": current_user}