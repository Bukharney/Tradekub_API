from typing import List
from fastapi import Depends, status, HTTPException, APIRouter
from app import api, oauth2, utils
from .. import models, schemas
from ..database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get(
    "/all",
    status_code=status.HTTP_200_OK,
)
def get_all_portfolio(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )
    result = db.query(models.Portfolio).all()
    return result


@router.get(
    "/{account_id}",
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.PortfolioOut],
)
def get_portfolio(
    account_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    account = (
        db.query(models.Accounts)
        .filter(models.Accounts.id == account_id)
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    if account.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    result = utils.get_portfolio(db=db, account_id=account_id)
    if not result:
        return []

    settrade = api.SetTradeSymbol()
    for symbol_info in result:
        price_info = settrade.get_price_info(symbol_info["symbol"])
        symbol_info["last_price"] = price_info.get("last", 0.0) or 0.0
        symbol_info["change"] = price_info.get("change", 0.0) or 0.0
        symbol_info["close"] = price_info.get("close", 0.0) or 0.0
        symbol_info["open"] = price_info.get("open", 0.0) or 0.0
        symbol_info["high"] = price_info.get("high", 0.0) or 0.0
        symbol_info["low"] = price_info.get("low", 0.0) or 0.0
        symbol_info["market_status"] = price_info.get("market_status", "CLOSED") or "CLOSED"

    return result


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
)
def create_portfolio(
    portfolio: schemas.PortfolioCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["admin", "broker"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Only brokers and admins can create portfolios",
        )

    user_account = (
        db.query(models.Accounts)
        .filter(models.Accounts.id == portfolio.account_id)
        .first()
    )
    if not user_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Target account not found"
        )

    if current_user.role == "broker":
        broker_account = (
            db.query(models.Accounts)
            .filter(models.Accounts.user_id == current_user.id)
            .first()
        )
        if not broker_account or broker_account.broker_id != user_account.broker_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only create portfolios for your own broker",
            )

    portfolio_exists = (
        db.query(models.Portfolio)
        .filter(models.Portfolio.account_id == portfolio.account_id)
        .filter(models.Portfolio.symbol == portfolio.symbol)
        .filter(models.Portfolio.price == portfolio.price)
        .first()
    )

    if portfolio_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Portfolio record already exists",
        )

    new_portfolio = models.Portfolio(**portfolio.model_dump())
    db.add(new_portfolio)
    db.commit()
    db.refresh(new_portfolio)
    return {
        "status": "success",
    }


@router.put(
    "/{portfolio_id}",
    status_code=status.HTTP_200_OK,
)
def update_portfolio(
    portfolio_id: int,
    portfolio: schemas.PortfolioCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["admin", "broker"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Only brokers and admins can update portfolios",
        )

    portfolio_exists = (
        db.query(models.Portfolio).filter(models.Portfolio.id == portfolio_id).first()
    )

    if not portfolio_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    db.query(models.Portfolio).filter(models.Portfolio.id == portfolio_id).update(
        portfolio.model_dump(exclude_unset=True)
    )
    db.commit()
    return {
        "status": "Update success!",
    }
