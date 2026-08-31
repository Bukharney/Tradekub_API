from typing import List
from fastapi import Depends, status, HTTPException, APIRouter
from app import oauth2, utils
from .. import models, schemas
from ..database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/order", tags=["Order"])


@router.post(
    "/",
    response_model=schemas.OrderOut,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    order: schemas.OrderCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    account = (
        db.query(models.Accounts).filter(models.Accounts.id == order.account_id).first()
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    if account.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this account"
        )

    symbol = db.query(models.Stock).filter(models.Stock.symbol == order.symbol).first()
    if not symbol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found"
        )

    if order.pin != account.pin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    order_dict = order.model_dump()
    order_dict.pop("pin", None)

    new_order = models.Orders(**order_dict)
    new_order.matched = 0
    new_order.balance = order.volume
    new_order.status = "O"
    new_order.cancelled = 0

    cost = order.volume * order.price

    port = utils.get_portfolio(db=db, account_id=order.account_id)

    if order.side == "Buy":
        if account.line_available < cost:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance"
            )
        account.line_available -= cost
    elif order.side == "Sell":
        if not port:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No stocks to sell"
            )
        stock_found = False
        for item in port:
            if item["symbol"] == order.symbol:
                stock_found = True
                if item["volume"] < order.volume:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="You don't have enough stocks to sell",
                    )
        if not stock_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No stocks of this symbol to sell"
            )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # Run order matching engine
    utils.transactions(db=db)
    db.refresh(new_order)

    return new_order


@router.get(
    "/all",
    status_code=status.HTTP_200_OK,
)
def get_all_orders_admin(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )
    orders = db.query(models.Orders).all()
    return orders


@router.get(
    "/endofday",
    status_code=status.HTTP_200_OK,
)
def end_of_day_orders(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can run end of day"
        )
    orders = db.query(models.Orders).filter(models.Orders.status == "O").all()
    for order in orders:
        order.cancelled = 1
        order.status = "C"
        account = (
            db.query(models.Accounts)
            .filter(models.Accounts.id == order.account_id)
            .first()
        )
        if account and order.side == "Buy":
            account.line_available += order.balance * order.price

    db.commit()
    return {
        "result": "End of day",
    }


@router.post(
    "/cancel",
    status_code=status.HTTP_200_OK,
)
def cancel_order_post(
    order: schemas.OrderCancel,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    db_order = db.query(models.Orders).filter(models.Orders.id == order.id).first()
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    if db_order.status == "C":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Order is already closed or cancelled"
        )

    account = (
        db.query(models.Accounts)
        .filter(models.Accounts.id == db_order.account_id)
        .first()
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    if account.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to cancel this order",
        )

    if account.pin != order.pin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    db_order.cancelled = 1
    db_order.status = "C"

    if db_order.side == "Buy":
        account.line_available += db_order.balance * db_order.price

    db.commit()
    db.refresh(db_order)
    return {
        "result": "Order cancelled successfully",
    }


@router.get(
    "/cancel/{id}",
    status_code=status.HTTP_200_OK,
)
def cancel_order_by_id(
    id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(models.Orders).filter(models.Orders.id == id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    if order.status == "C":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Order is already closed or cancelled"
        )

    account = (
        db.query(models.Accounts).filter(models.Accounts.id == order.account_id).first()
    )
    if not account or (account.user_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to cancel this order",
        )

    order.cancelled = 1
    order.status = "C"

    if order.side == "Buy":
        account.line_available += order.balance * order.price

    db.commit()
    db.refresh(order)
    return {
        "result": "Order cancelled successfully",
    }


@router.get(
    "/one/{id}",
    response_model=schemas.OrderOut,
    status_code=status.HTTP_200_OK,
)
def get_order_by_id(
    id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(models.Orders).filter(models.Orders.id == id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    account = (
        db.query(models.Accounts).filter(models.Accounts.id == order.account_id).first()
    )
    if account and account.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    return order


@router.put(
    "/update",
    status_code=status.HTTP_200_OK,
)
def update_orders(
    order: schemas.OrderUpdate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["admin", "broker"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to update this order",
        )

    db_order = db.query(models.Orders).filter(models.Orders.id == order.id).first()
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    account = (
        db.query(models.Accounts)
        .filter(models.Accounts.id == db_order.account_id)
        .first()
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    if db_order.status == "O":
        if db_order.side == "Buy":
            if order.side == "Buy":
                account.line_available += db_order.balance * db_order.price
                account.line_available -= order.balance * order.price
            elif order.side == "Sell":
                account.line_available += db_order.balance * db_order.price
        elif db_order.side == "Sell":
            if order.side == "Buy":
                account.line_available -= order.balance * order.price

    db_order.price = order.price
    db_order.volume = order.volume
    db_order.balance = order.balance
    db_order.status = order.status
    db_order.side = order.side
    db_order.type = order.type
    db_order.matched = order.matched
    db_order.cancelled = order.cancelled
    db_order.account_id = order.account_id
    db_order.symbol = order.symbol
    db_order.validity = order.validity

    db.commit()
    db.refresh(db_order)
    return {
        "result": "Order updated successfully",
    }


@router.get(
    "/{account_id}",
    response_model=List[schemas.OrderOut],
    status_code=status.HTTP_200_OK,
)
def get_account_orders(
    account_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    account = (
        db.query(models.Accounts).filter(models.Accounts.id == account_id).first()
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    if account.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    orders = (
        db.query(models.Orders)
        .filter(models.Orders.account_id == account_id)
        .order_by(models.Orders.time.desc())
        .all()
    )
    return orders
