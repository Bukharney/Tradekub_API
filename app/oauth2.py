from typing import Optional
from jose import JWTError, jwt
from datetime import datetime, timedelta

from app import utils
from . import schemas, database, models
from fastapi import Depends, status, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_access_token(token: str, credentials_exception):
    try:
        clean_token = token.strip('"\'')
        if clean_token.startswith("Bearer ") or clean_token.startswith("bearer "):
            clean_token = clean_token[7:].strip('"\'')

        payload = jwt.decode(clean_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            print(f"DEBUG JWT: user_id is None in token payload: {payload}")
            raise credentials_exception
        token_data = schemas.TokenData(id=user_id)
    except JWTError as e:
        print(f"DEBUG JWTError: '{e}' for token: '{token}'")
        raise credentials_exception

    return token_data


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Fallbacks if OAuth2PasswordBearer did not catch the token
    if not token:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_header:
            if auth_header.startswith("Bearer ") or auth_header.startswith("bearer "):
                token = auth_header[7:].strip()
            else:
                token = auth_header.strip()
        elif "token" in request.cookies:
            token = request.cookies.get("token")
        elif "access_token" in request.cookies:
            token = request.cookies.get("access_token")

    if not token or token == "undefined" or token == "null":
        print("DEBUG Auth: No valid token provided in headers or cookies!")
        raise credentials_exception

    token_data = verify_access_token(token, credentials_exception)

    try:
        user_id = int(token_data.id)
    except (ValueError, TypeError):
        print(f"DEBUG Auth: Invalid user_id format '{token_data.id}'")
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        print(f"DEBUG Auth: User with ID {user_id} not found in database!")
        raise credentials_exception

    return user


def get_current_user_optional(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db),
) -> Optional[models.User]:
    try:
        return get_current_user(request, token, db)
    except HTTPException:
        return None
