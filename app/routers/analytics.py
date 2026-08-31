from fastapi import Depends, status, HTTPException, APIRouter
from sqlalchemy import case, func, text
from ..database import get_db
from sqlalchemy.orm import Session
from app import oauth2, models

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/most_vol_stock/{start_time}/{end_time}",
    status_code=status.HTTP_200_OK,
)
def get_most_vol(
    start_time: str,
    end_time: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    sql = text(
        """
    SELECT
        orders.symbol,
        SUM(transactions.volume) AS vol_sum,
        AVG(transactions.price) AS price_avg,
        COUNT(DISTINCT CASE WHEN orders.side = 'Sell' THEN orders.id END) AS total_sell_order,
        COUNT(DISTINCT CASE WHEN orders.side = 'Buy' THEN orders.id END) AS total_buy_order
    FROM
        orders
    JOIN 
        transactions
    ON transactions.order_id = orders.id
    WHERE 
        orders.time BETWEEN :start_time AND :end_time
    GROUP BY orders.symbol
    ORDER BY vol_sum DESC
        """
    ).bindparams(start_time=start_time, end_time=end_time)

    result = db.execute(sql).fetchall()

    orders = [
        {
            "symbol": row.symbol,
            "vol_sum": row.vol_sum or 0,
            "price_avg": round(row.price_avg, 2) if row.price_avg is not None else 0.0,
            "total_buy_order": row.total_buy_order or 0,
            "total_sell_order": row.total_sell_order or 0,
        }
        for row in result
    ]
    return orders


@router.get(
    "/most_new_contract_broker/{start_time}/{end_time}",
    status_code=status.HTTP_200_OK,
)
def get_most_contrac(
    start_time: str,
    end_time: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    sql = text(
        """
    SELECT
        brokers.name,
        COUNT(CASE WHEN accounts.created_at BETWEEN :start_time AND :end_time THEN accounts.id END) AS new_accounts,
        COUNT(CASE WHEN accounts.created_at < :start_time THEN accounts.id END) AS total_accounts_before,
        COUNT(CASE WHEN accounts.created_at < :end_time THEN accounts.id END) AS total_accounts_endtime,
        (COUNT(CASE WHEN accounts.created_at BETWEEN :start_time AND :end_time THEN accounts.id END) * 100.0) / 
            NULLIF(COUNT(CASE WHEN accounts.created_at < :start_time THEN accounts.id END), 0) as percentage_new_users,
        COUNT (DISTINCT users.id) as total_users
    FROM
        users
    JOIN
        accounts
    ON 
        accounts.user_id = users.id
    JOIN
        brokers
    ON
        brokers.id = accounts.broker_id
    GROUP BY
        brokers.id, brokers.name
    ORDER BY new_accounts DESC
        """
    ).bindparams(start_time=start_time, end_time=end_time)

    result = db.execute(sql).fetchall()

    orders = [
        {
            "broker_name": row.name,
            "new_accounts": row.new_accounts or 0,
            "total_accounts_before": row.total_accounts_before or 0,
            "total_accounts_endtime": row.total_accounts_endtime or 0,
            "percentage_new_users": round(row.percentage_new_users, 2) if row.percentage_new_users is not None else 0.0,
            "total_users": row.total_users or 0,
        }
        for row in result
    ]
    return orders


@router.get(
    "/most_cancel_ratio/{start_time}/{end_time}",
    status_code=status.HTTP_200_OK,
)
def get_most_cancel(
    start_time: str,
    end_time: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    sql = text(
        """
    SELECT
        stocks.company_name,
        stocks.symbol,
        DATE(orders.time) AS order_date,
        AVG(CASE WHEN orders.cancelled = 0 THEN orders.price END) AS average_price,
        (COUNT(CASE WHEN orders.cancelled = 1 THEN orders.id END) * 100.0) / 
        NULLIF(COUNT(orders.id), 0) AS cancel_rate
    FROM
        stocks
    JOIN
        orders
    ON 
        stocks.symbol = orders.symbol
    WHERE
        orders.time BETWEEN :start_time AND :end_time
    GROUP BY 
        stocks.company_name, stocks.symbol, DATE(orders.time)
    ORDER BY 
        cancel_rate DESC   
        """
    ).bindparams(start_time=start_time, end_time=end_time)

    result = db.execute(sql).fetchall()

    orders = [
        {
            "company_name": row.company_name,
            "symbol": row.symbol,
            "order_date": str(row.order_date) if row.order_date else "",
            "average_price": round(row.average_price, 2) if row.average_price is not None else 0.0,
            "cancel_rate": round(row.cancel_rate, 2) if row.cancel_rate is not None else 0.0,
        }
        for row in result
    ]
    return orders


@router.get(
    "/most_closed_value/{start_time}/{end_time}",
    status_code=status.HTTP_200_OK,
)
def get_most_closed_value(
    start_time: str,
    end_time: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    sql = text(
        """
    SELECT
        stocks.company_name,
        stocks.symbol,
        DATE(orders.time) AS date,
        SUM(orders.matched) AS volume,
        SUM(orders.price * orders.matched) AS value,
        COUNT(DISTINCT users.id) AS total_users
    FROM
        stocks
    JOIN
        orders
    ON 
        stocks.symbol = orders.symbol
    JOIN
        accounts
    ON 
        accounts.id = orders.account_id
    JOIN
        users
    ON 
        users.id = accounts.user_id
    WHERE
        orders.time BETWEEN :start_time AND :end_time AND orders.status = 'C'
    GROUP BY  
        stocks.company_name, stocks.symbol, DATE(orders.time)
    ORDER BY 
        value DESC
        """
    ).bindparams(start_time=start_time, end_time=end_time)

    result = db.execute(sql).fetchall()

    orders = [
        {
            "company_name": row.company_name,
            "symbol": row.symbol,
            "date": str(row.date) if row.date else "",
            "volume": row.volume or 0,
            "value": round(row.value, 2) if row.value is not None else 0.0,
            "total_users": row.total_users or 0,
        }
        for row in result
    ]
    return orders
