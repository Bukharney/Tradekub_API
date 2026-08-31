from typing import List
from fastapi import Depends, status, HTTPException, APIRouter
from app import oauth2, utils
from .. import models, schemas
from ..database import get_db
from sqlalchemy.orm import Session


router = APIRouter(prefix="/account", tags=["Account"])


@router.get("/all")
def get_all_accounts_admin(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view all accounts",
        )
    accounts = db.query(models.Accounts).all()
    return accounts


@router.get("/my", response_model=List[schemas.AccountOut])
def get_my_accounts(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    accounts = (
        db.query(models.Accounts)
        .filter(models.Accounts.user_id == current_user.id)
        .all()
    )
    return accounts


@router.get("/{account_id}")
def get_account(
    account_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    account = db.query(models.Accounts).filter(models.Accounts.id == account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )
    broker = (
        db.query(models.Broker).filter(models.Broker.id == account.broker_id).first()
    )

    account_dict = {
        "id": account.id,
        "user_id": account.user_id,
        "broker_id": account.broker_id,
        "broker_name": broker.name if broker else "Unknown",
        "cash_balance": account.cash_balance,
        "line_available": account.line_available,
        "credit_limit": account.credit_limit,
    }
    return account_dict


@router.get(
    "/verify_balance/{account_id}",
    status_code=status.HTTP_200_OK,
)
def verify_account_balance(
    account_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["admin", "broker"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to perform this action",
        )

    account = db.query(models.Accounts).filter(models.Accounts.id == account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    if current_user.role == "broker":
        broker_account = (
            db.query(models.Accounts)
            .filter(models.Accounts.user_id == current_user.id)
            .first()
        )
        if not broker_account or broker_account.broker_id != account.broker_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to perform this action",
            )

    account.cash_balance = account.line_available
    db.commit()
    db.refresh(account)

    return {
        "result": "success",
    }


@router.post(
    "/", response_model=schemas.AccountOut, status_code=status.HTTP_201_CREATED
)
def create_account(
    account: schemas.AccountCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    broker = (
        db.query(models.Broker).filter(models.Broker.id == account.broker_id).first()
    )
    if not broker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Given broker not found"
        )

    new_account = models.Accounts(**account.model_dump())
    try:
        db.add(new_account)
        db.commit()
        db.refresh(new_account)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return new_account


@router.put(
    "/{account_id}",
    status_code=status.HTTP_200_OK,
)
def update_account(
    account_id: int,
    account: schemas.AccountCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["admin", "broker"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to perform this action",
        )

    account_db = (
        db.query(models.Accounts).filter(models.Accounts.id == account_id).first()
    )
    if not account_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    for key, value in account.model_dump().items():
        if value is not None:
            setattr(account_db, key, value)

    db.commit()
    db.refresh(account_db)

    return {
        "result": "success",
    }


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_200_OK,
)
def delete_account(
    account_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["admin", "broker"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to perform this action",
        )

    account_db = (
        db.query(models.Accounts).filter(models.Accounts.id == account_id).first()
    )
    if not account_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    try:
        db.delete(account_db)
        db.commit()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return {
        "result": "success",
    }
