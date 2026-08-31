from sqlalchemy import (
    Column,
    Date,
    Integer,
    String,
    ForeignKey,
    Float,
    BigInteger,
    Numeric,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import TIMESTAMP

from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, nullable=False)
    role = Column(String, nullable=False, default="user")
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class Broker(Base):
    __tablename__ = "brokers"
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    api_key = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class Stock(Base):
    __tablename__ = "stocks"
    symbol = Column(
        String,
        primary_key=True,
        nullable=False,
    )
    company_name = Column(String, nullable=False)
    stock_industry = Column(String, nullable=False)
    market_value = Column(BigInteger, nullable=False)
    volume = Column(BigInteger, nullable=False)
    address = Column(String, nullable=False)
    telephone = Column(String, nullable=False)
    website = Column(String, nullable=False)
    registered_capital = Column(BigInteger, nullable=False)
    established_date = Column(Date, nullable=False)
    market_entry_date = Column(Date, nullable=False)
    ipo_price = Column(Float, nullable=False)
    free_float = Column(Integer, nullable=False)
    major_shareholders = Column(Integer, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class Login_Logout(Base):
    __tablename__ = "login_logout"
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    login = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    logout = Column(TIMESTAMP(timezone=True))
    device = Column(String)
    ip = Column(String)


class Accounts(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    broker_id = Column(Integer, ForeignKey("brokers.id"))
    cash_balance = Column(Float, nullable=False)
    line_available = Column(Float, nullable=False)
    credit_limit = Column(Float, nullable=False)
    pin = Column(Integer, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class Bank_transactions(Base):
    __tablename__ = "bank_tsc"
    id = Column(Integer, primary_key=True, nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    account_number = Column(String, nullable=False)
    type = Column(String, nullable=False)
    amount = Column(Numeric, nullable=False)
    timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class Orders(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    symbol = Column(String, ForeignKey("stocks.symbol"))
    balance = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    side = Column(String, nullable=False)
    matched = Column(Integer, nullable=False)
    cancelled = Column(Integer, nullable=False)
    validity = Column(String, nullable=False)
    time = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class Transactions(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"))
    price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class Turnover(Base):
    __tablename__ = "turnover"
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    symbol = Column(String, ForeignKey("stocks.symbol"), nullable=False)
    asset = Column(Integer)
    dept = Column(Integer)
    pbv = Column(Numeric, nullable=False)
    eps = Column(Numeric, nullable=False)
    dividend_per_unit = Column(Integer)
    net_profit = Column(Integer)
    timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Dividend(Base):
    __tablename__ = "dividend"
    id = Column(Integer, primary_key=True, nullable=False)
    symbol = Column(String, ForeignKey("stocks.symbol"))
    account_id = Column(Integer, ForeignKey("accounts.id"))
    value = Column(Float, nullable=False)
    timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True, nullable=False)
    file = Column(String)
    topic = Column(String, nullable=False)
    content = Column(String, nullable=False)
    news_time = Column(TIMESTAMP(timezone=True), nullable=False)


class Portfolio(Base):
    __tablename__ = "portfolio"
    id = Column(Integer, primary_key=True, nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    symbol = Column(String, ForeignKey("stocks.symbol"))
    volume = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class Notifications(Base):
    __tablename__ = "notification"
    id = Column(Integer, primary_key=True, nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    message = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
