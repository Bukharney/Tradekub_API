import datetime
from fastapi import Depends, status, HTTPException, APIRouter
from app import oauth2, utils
from .. import models, schemas
from ..database import get_db
from sqlalchemy.orm import Session
from typing import List


router = APIRouter(prefix="/bank_tsc", tags=["Bank Transaction"])


@router.post(
    "/",
    response_model=schemas.BankTransactionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_bank_transaction(
    bank_transaction: schemas.BankTransactionCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["admin", "broker"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to create bank transactions",
        )

    account = (
        db.query(models.Accounts)
        .filter(models.Accounts.id == bank_transaction.account_id)
        .first()
    )
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
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only create bank transactions for your own broker",
            )

    tsc_type = bank_transaction.type.lower()
    if tsc_type == "deposit":
        account.cash_balance += bank_transaction.amount
        account.line_available += bank_transaction.amount
    elif tsc_type == "withdraw":
        if account.line_available < bank_transaction.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough funds in account",
            )
        account.cash_balance -= bank_transaction.amount
        account.line_available -= bank_transaction.amount
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bank transaction type must be deposit or withdraw",
        )

    new_bank_transaction = models.Bank_transactions(**bank_transaction.model_dump())
    new_bank_transaction.type = tsc_type
    db.add(new_bank_transaction)
    db.commit()
    db.refresh(new_bank_transaction)
    return new_bank_transaction


@router.get(
    "/",
)
def get_all_bank_transactions(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["admin", "broker"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )
    bank_transactions = db.query(models.Bank_transactions).all()
    return bank_transactions


@router.get(
    "/my/{account_id}",
    response_model=List[schemas.BankTransactionOut],
)
def get_bank_transactions(
    account_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    account = (
        db.query(models.Accounts)
        .filter(models.Accounts.id == account_id)
        .filter(models.Accounts.user_id == current_user.id)
        .first()
    )
    if not account and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    bank_transactions = (
        db.query(models.Bank_transactions)
        .filter(models.Bank_transactions.account_id == account_id)
        .order_by(models.Bank_transactions.timestamp.desc())
        .all()
    )

    if not bank_transactions:
        return []
    return bank_transactions


@router.get(
    "/{id}",
    response_model=schemas.BankTransactionOut,
)
def get_bank_transaction(
    id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    bank_transaction = (
        db.query(models.Bank_transactions)
        .filter(models.Bank_transactions.id == id)
        .first()
    )
    if not bank_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bank Transaction not found"
        )

    return bank_transaction


@router.put(
    "/{id}",
    response_model=schemas.BankTransactionOut,
)
def update_bank_transaction(
    id: int,
    bank_transaction: schemas.BankTransactionCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["admin", "broker"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to update bank transactions",
        )

    db_bank_transaction = (
        db.query(models.Bank_transactions)
        .filter(models.Bank_transactions.id == id)
        .first()
    )
    if not db_bank_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bank Transaction not found"
        )

    user_account = (
        db.query(models.Accounts)
        .filter(models.Accounts.id == db_bank_transaction.account_id)
        .first()
    )

    if not user_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User does not have account"
        )

    new_type = bank_transaction.type.lower()
    old_type = db_bank_transaction.type.lower()
    old_amount = float(db_bank_transaction.amount)
    new_amount = float(bank_transaction.amount)


    # Revert old transaction effect
    if old_type == "deposit":
        user_account.cash_balance -= old_amount
        user_account.line_available -= old_amount
    elif old_type == "withdraw":
        user_account.cash_balance += old_amount
        user_account.line_available += old_amount

    # Apply new transaction effect
    if new_type == "deposit":
        user_account.cash_balance += new_amount
        user_account.line_available += new_amount
    elif new_type == "withdraw":
        if user_account.line_available < new_amount:
            # Re-apply old transaction before raising error
            if old_type == "deposit":
                user_account.cash_balance += old_amount
                user_account.line_available += old_amount
            elif old_type == "withdraw":
                user_account.cash_balance -= old_amount
                user_account.line_available -= old_amount
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough funds in account for updated withdrawal",
            )
        user_account.cash_balance -= new_amount
        user_account.line_available -= new_amount
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bank transaction type must be deposit or withdraw",
        )

    db_bank_transaction.amount = new_amount
    db_bank_transaction.type = new_type
    db_bank_transaction.timestamp = utils.get_current_time()
    db_bank_transaction.account_id = bank_transaction.account_id
    db_bank_transaction.account_number = bank_transaction.account_number

    db.commit()
    db.refresh(db_bank_transaction)
    return db_bank_transaction
