from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from core.database import get_session
from models.identity import Users
from core.config import settings

router = APIRouter(
    prefix = '/auth',
    tags =  ['auth']
)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl = 'auth/token')

class CreateUserRequest(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

db_dependency = Annotated[Session, Depends(get_session)]
    
# End-point: create new user and add it to database
@router.post("/", status_code = status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):
    existing = db.exec(select(Users).where(Users.email == create_user_request.email)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    create_user_model = Users(
        email = create_user_request.email, 
        password_hash = pwd_context.hash(create_user_request.password)
    )

    db.add(create_user_model)
    db.commit()
    return {"message": "User created successfully"}

# Queries User table and authenticate user
def authenticate_user(email: str, password: str, db: Session):
    user = db.exec(select(Users).where(Users.email == email)).one_or_none()
    if not user:
        return False
    if not pwd_context.verify(password, user.password_hash):
        return False
    return user

# Encode JWT
def create_access_token(email: str, user_id: int, expires_after: timedelta):
    expires = datetime.now(timezone.utc) + expires_after
    encode = {'sub': email, 'id': user_id, 'exp': expires}
    return jwt.encode(encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# Decode JWT
async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.ALGORITHM)
        email: str = payload.get('sub')
        user_id: int = payload.get('id')
        if email is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Couldn't validate user")
        return {'email': email, 'id': user_id}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Couldn't validate user")

# End-point: Login and get JWT token
@router.post("/token", response_model = Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
                                 db: db_dependency):
    # Note: form_data.username is used by FastAPI's OAuth2PasswordRequestForm 
    # to store the principal identity field, which in our case is the email.
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is deactivated")
    
    token = create_access_token(user.email, user.id, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return {'access_token': token, 'token_type': 'bearer'}
