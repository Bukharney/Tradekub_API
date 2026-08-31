from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime, date
from typing import Optional


class UserOut(BaseModel):
    id: int
    name: str
    phone: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    name: str
    phone: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


from typing import Optional, Union


class TokenData(BaseModel):
    id: Optional[Union[str, int]] = None



class Account(BaseModel):
    id: int


class AccountCreate(BaseModel):
    user_id: int
    broker_id: int
    cash_balance: float
    line_available: float
    credit_limit: float
    pin: int


class AccountOut(Account):
    broker_id: int
    cash_balance: float
    line_available: float
    credit_limit: float

    model_config = ConfigDict(from_attributes=True)


class StockCreate(BaseModel):
    symbol: str
    company_name: str
    stock_industry: str
    market_value: int
    volume: int
    address: str
    telephone: str
    website: str
    registered_capital: int
    established_date: date
    market_entry_date: date
    ipo_price: float
    free_float: int
    major_shareholders: int

    model_config = ConfigDict(from_attributes=True)


class StockOut(BaseModel):
    symbol: str
    company_name: str

    model_config = ConfigDict(from_attributes=True)


class StockOutMarket(BaseModel):
    symbol: str
    close: float
    open: float
    change: float
    value: float

    model_config = ConfigDict(from_attributes=True)


class BrokerOut(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)


class BrokerCreate(BaseModel):
    name: str
    api_key: str

    model_config = ConfigDict(from_attributes=True)


class BankTransactionCreate(BaseModel):
    account_id: int
    account_number: str
    type: str
    amount: float

    model_config = ConfigDict(from_attributes=True)


class BankTransactionOut(BaseModel):
    id: int
    type: str
    amount: float
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    account_id: int
    symbol: str
    type: str
    volume: int
    price: float
    side: str
    validity: str
    pin: int

    model_config = ConfigDict(from_attributes=True)


class OrderUpdate(OrderCreate):
    id: int
    status: str
    balance: int
    matched: int
    cancelled: int

    model_config = ConfigDict(from_attributes=True)


class OrderCancel(BaseModel):
    id: int
    pin: int

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: int
    account_id: int
    symbol: str
    type: str
    volume: int
    price: float
    side: str
    validity: str
    time: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)


class StockSearch(BaseModel):
    symbol: str
    close: float
    change: float


class DividendCreate(BaseModel):
    symbol: str
    account_id: int
    value: float

    model_config = ConfigDict(from_attributes=True)


class DividendOut(DividendCreate):
    id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class NotiOut(BaseModel):
    id: int
    message: str
    volume: int
    price: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortfolioCreate(BaseModel):
    account_id: int
    symbol: str
    volume: int
    price: float

    model_config = ConfigDict(from_attributes=True)


class PortfolioOut(BaseModel):
    symbol: str
    volume: int
    avg_price: float
    last_price: float = 0.0
    change: float = 0.0
    open: float = 0.0
    close: float = 0.0
    high: float = 0.0
    low: float = 0.0
    market_status: str = "CLOSED"

    model_config = ConfigDict(from_attributes=True)


class LoginOut(BaseModel):
    login: datetime
    device: Optional[str] = None
    ip: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(BaseModel):
    order_id: int
    price: float
    volume: int

    model_config = ConfigDict(from_attributes=True)
