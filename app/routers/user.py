from typing import List
from fastapi import Depends, status, HTTPException, APIRouter

from app import oauth2

from .. import models, schemas, utils
from ..database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with given email already exists",
        )

    hash_pw = utils.hash_password(user.password)
    user_dict = user.model_dump()
    user_dict["password"] = hash_pw
    new_user = models.User(**user_dict)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Ensure a default broker exists before creating initial account
    default_broker = db.query(models.Broker).filter(models.Broker.id == 1).first()
    if not default_broker:
        default_broker = models.Broker(id=1, name="Default Broker", api_key="default_key")
        db.add(default_broker)
        db.commit()
        db.refresh(default_broker)

    account = models.Accounts(
        user_id=new_user.id,
        broker_id=default_broker.id,
        cash_balance=500000.0,
        line_available=500000.0,
        credit_limit=500000.0,
        pin=123456,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return new_user


@router.get("/", response_model=List[schemas.UserOut])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )
    users = db.query(models.User).all()
    return users


@router.get("/token", response_model=schemas.UserOut)
def get_user_by_token(
    current_user: models.User = Depends(oauth2.get_current_user),
):
    return current_user


@router.get("/username/{symbol}", response_model=schemas.UserOut)
def get_user_by_name(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    user = db.query(models.User).filter(models.User.name == symbol).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.get("/my", response_model=schemas.UserOut)
def get_current_user_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    return current_user


@router.get("/login_info", response_model=List[schemas.LoginOut])
def get_user_login_info(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    logins = (
        db.query(models.Login_Logout)
        .filter(models.Login_Logout.user_id == current_user.id)
        .order_by(models.Login_Logout.id.desc())
        .all()
    )

    if not logins:
        return []
    return logins


@router.get("/login_info/all")
def get_all_login_info(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )
    logins = db.query(models.Login_Logout).order_by(models.Login_Logout.id.desc()).all()
    return logins


@router.put(
    "/update",
    response_model=schemas.UserOut,
    status_code=status.HTTP_200_OK,
)
def update_user(
    new_user: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user.name = new_user.name
    user.email = new_user.email
    user.password = utils.hash_password(new_user.password)
    user.phone = new_user.phone
    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/delete",
    status_code=status.HTTP_200_OK,
)
def delete_user(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    db.delete(user)
    db.commit()

    return {"detail": "User deleted successfully"}


@router.get("/{id}", response_model=schemas.UserOut)
def get_user_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with given id not found",
        )
    return user
