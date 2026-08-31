from typing import List
from fastapi import Depends, status, HTTPException, APIRouter
from app import oauth2, api, utils
from .. import models, schemas
from ..database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/stock", tags=["Stock"])


@router.post("/", response_model=schemas.StockOut, status_code=status.HTTP_201_CREATED)
def create_stock(
    stock: schemas.StockCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["admin", "company"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to create a stock",
        )

    stock.symbol = stock.symbol.upper()
    existing_stock = (
        db.query(models.Stock).filter(models.Stock.symbol == stock.symbol).first()
    )
    if existing_stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock with given symbol already exists",
        )

    new_stock = models.Stock(**stock.model_dump())
    db.add(new_stock)
    db.commit()
    db.refresh(new_stock)
    return new_stock


@router.get("/", response_model=List[schemas.StockOutMarket])
def get_all_stocks(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    stocks = db.query(models.Stock).all()
    if not stocks:
        return []

    settrade = api.SetTradeSymbol()
    settrade.get_candlesticks(stocks, "1d", 1)
    sorted_stocks = sorted(stocks, key=lambda x: getattr(x, "value", 0.0), reverse=True)
    return sorted_stocks


@router.get("/company_info/all")
def stock_comp_info(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    info = db.query(models.Stock).all()
    return info


@router.get("/search/{symbol}", response_model=List[schemas.StockOutMarket])
def get_stock_search(
    symbol: str,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    symbol = symbol.upper()
    result = (
        db.query(models.Stock).filter(models.Stock.symbol.like(f"%{symbol}%")).all()
    )
    if not result:
        return []

    settrade = api.SetTradeSymbol()
    settrade.get_candlesticks(result, "1d", 1)
    return result


@router.get("/market/{symbol}/{interval}/{limit}")
def get_stock_market(
    symbol: str,
    interval: str,
    limit: int,
    period: str = None,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    res = api.SetTradeSymbol().get_candlestick(symbol.upper(), interval, limit, period=period)

    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stock market data not found"
        )

    return res


@router.get("/price_info/{symbol}")
def get_stock_market_price_info(
    symbol: str,
    current_user: models.User = Depends(oauth2.get_current_user),
):
    res = api.SetTradeSymbol().get_price_info(symbol.upper())

    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Something went wrong"
        )

    return res


@router.get("/bid_offer/{symbol}")
def get_stock_market_bid_offer(
    symbol: str,
    current_user: models.User = Depends(oauth2.get_current_user),
):
    res = api.SetTradeSymbol().get_bid_offer(symbol.upper())

    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Something went wrong"
        )

    return res


@router.get("/transactions/all")
def get_all_transactions(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )
    transactions = db.query(models.Transactions).all()
    return transactions


@router.get("/transactions/{account_id}")
def get_my_transactions(
    account_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    account = (
        db.query(models.Accounts).filter(models.Accounts.id == account_id).first()
    )
    if not account or (account.user_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    transactions = (
        db.query(models.Transactions)
        .join(
            models.Orders,
            models.Transactions.order_id == models.Orders.id,
        )
        .filter(models.Orders.account_id == account_id)
        .order_by(models.Transactions.timestamp.desc())
        .all()
    )

    result = []
    for t in transactions:
        order = (
            db.query(models.Orders)
            .filter(models.Orders.id == t.order_id)
            .first()
        )
        result.append({
            "id": t.id,
            "order_id": t.order_id,
            "price": t.price,
            "volume": t.volume,
            "timestamp": t.timestamp,
            "symbol": order.symbol if order else "Unknown",
            "side": order.side if order else "Unknown",
        })

    return result


@router.get("/market_data/{symbol}")
def get_stock_market_data(
    symbol: str,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    return api.SetTradeSymbol().get_market_data(symbol.upper())


@router.put("/update/{symbol}")
def update_stock(
    symbol: str,
    update_stock: schemas.StockCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["admin", "company"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to update a stock",
        )

    symbol_str = symbol.upper()
    stock = db.query(models.Stock).filter(models.Stock.symbol == symbol_str).first()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found"
        )

    for key, value in update_stock.model_dump().items():
        if key == "symbol":
            setattr(stock, key, value.upper())
        else:
            setattr(stock, key, value)

    db.commit()
    db.refresh(stock)

    return stock


@router.delete("/delete/{symbol}")
def delete_stock(
    symbol: str,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["admin", "company"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to delete a stock",
        )

    symbol_str = symbol.upper()
    stock = db.query(models.Stock).filter(models.Stock.symbol == symbol_str).first()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found"
        )

    db.delete(stock)
    db.commit()

    return {"message": "Stock deleted successfully"}


@router.post("/transactions")
def create_transaction(
    transaction: schemas.TransactionCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["admin", "broker"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to create a transaction",
        )

    order = db.query(models.Orders).filter(models.Orders.id == transaction.order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    new_transaction = models.Transactions(
        order_id=transaction.order_id,
        price=transaction.price,
        volume=transaction.volume,
    )
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    return new_transaction


@router.get("/{symbol}", response_model=schemas.StockCreate)
def get_stock(
    symbol: str,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    stock = db.query(models.Stock).filter(models.Stock.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found"
        )

    return stock
