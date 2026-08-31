import datetime
import bcrypt
from app import api
from . import models


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify(password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = password.encode("utf-8")[:72]
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False


def get_current_time() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def transactions(db):
    buy_orders = (
        db.query(models.Orders)
        .filter(
            models.Orders.side == "Buy",
            models.Orders.status == "O",
        )
        .order_by(models.Orders.price.desc(), models.Orders.time.asc())
        .all()
    )

    sell_orders = (
        db.query(models.Orders)
        .filter(
            models.Orders.side == "Sell",
            models.Orders.status == "O",
        )
        .order_by(models.Orders.price.asc(), models.Orders.time.asc())
        .all()
    )

    if not buy_orders or not sell_orders:
        return True

    for buy_order in buy_orders:
        if buy_order.status == "C" or buy_order.balance <= 0:
            continue

        for sell_order in sell_orders:
            if sell_order.status == "C" or sell_order.balance <= 0:
                continue

            if buy_order.account_id == sell_order.account_id:
                continue

            if buy_order.symbol != sell_order.symbol:
                continue

            if buy_order.price < sell_order.price:
                continue

            # Calculate match volume and execution price
            matched_volume = min(buy_order.balance, sell_order.balance)
            execution_price = sell_order.price
            trade_value = matched_volume * execution_price

            buyer_account = (
                db.query(models.Accounts)
                .filter(models.Accounts.id == buy_order.account_id)
                .first()
            )
            seller_account = (
                db.query(models.Accounts)
                .filter(models.Accounts.id == sell_order.account_id)
                .first()
            )

            # Record transactions
            buy_transaction = models.Transactions(
                order_id=buy_order.id,
                price=execution_price,
                volume=matched_volume,
            )
            sell_transaction = models.Transactions(
                order_id=sell_order.id,
                price=execution_price,
                volume=matched_volume,
            )
            db.add(buy_transaction)
            db.add(sell_transaction)

            # Update Portfolios
            buyer_portfolio = (
                db.query(models.Portfolio)
                .filter(
                    models.Portfolio.account_id == buy_order.account_id,
                    models.Portfolio.symbol == buy_order.symbol,
                )
                .first()
            )
            if not buyer_portfolio:
                buyer_portfolio = models.Portfolio(
                    account_id=buy_order.account_id,
                    symbol=buy_order.symbol,
                    volume=0,
                    price=execution_price,
                )
                db.add(buyer_portfolio)

            seller_portfolio = (
                db.query(models.Portfolio)
                .filter(
                    models.Portfolio.account_id == sell_order.account_id,
                    models.Portfolio.symbol == sell_order.symbol,
                )
                .first()
            )
            if not seller_portfolio:
                seller_portfolio = models.Portfolio(
                    account_id=sell_order.account_id,
                    symbol=sell_order.symbol,
                    volume=0,
                    price=execution_price,
                )
                db.add(seller_portfolio)

            buyer_portfolio.volume += matched_volume
            buyer_portfolio.price = execution_price

            seller_portfolio.volume -= matched_volume
            seller_portfolio.price = execution_price

            # Update account cash & line balances
            if seller_account:
                seller_account.cash_balance += trade_value
                seller_account.line_available += trade_value

            if buyer_account:
                buyer_account.cash_balance -= trade_value
                # Refund line available if matched price was lower than buy limit price
                price_savings = (buy_order.price - execution_price) * matched_volume
                if price_savings > 0:
                    buyer_account.line_available += price_savings

            # Update order states
            buy_order.balance -= matched_volume
            buy_order.matched += matched_volume

            sell_order.balance -= matched_volume
            sell_order.matched += matched_volume

            if buy_order.balance == 0:
                buy_order.status = "C"
                buyer_msg = f"Your order BUY: {buy_order.symbol} was executed and closed"
            else:
                buyer_msg = f"Your order BUY: {buy_order.symbol} was partially executed"

            if sell_order.balance == 0:
                sell_order.status = "C"
                seller_msg = f"Your order SELL: {sell_order.symbol} was executed and closed"
            else:
                seller_msg = f"Your order SELL: {sell_order.symbol} was partially executed"

            # Create Notifications
            buyer_noti = models.Notifications(
                account_id=buy_order.account_id,
                message=buyer_msg,
                price=execution_price,
                volume=matched_volume,
            )
            seller_noti = models.Notifications(
                account_id=sell_order.account_id,
                message=seller_msg,
                price=execution_price,
                volume=matched_volume,
            )
            db.add(buyer_noti)
            db.add(seller_noti)

            db.commit()

            if buy_order.balance == 0:
                break

    return True


def get_portfolio(db, account_id: int):
    port_items = (
        db.query(models.Portfolio)
        .filter(models.Portfolio.account_id == account_id)
        .all()
    )

    if not port_items:
        return False

    symbol_data = {}

    for item in port_items:
        symbol = item.symbol
        volume = item.volume
        price = item.price

        if symbol not in symbol_data:
            symbol_data[symbol] = {"volume": 0, "total_cost": 0.0}

        if volume > 0:
            symbol_data[symbol]["volume"] += volume
            symbol_data[symbol]["total_cost"] += volume * price
        else:
            # Sell transaction reduces volume and cost basis proportionally
            curr_vol = symbol_data[symbol]["volume"]
            if curr_vol > 0:
                avg_cost = symbol_data[symbol]["total_cost"] / curr_vol
                sell_vol = min(abs(volume), curr_vol)
                symbol_data[symbol]["volume"] -= sell_vol
                symbol_data[symbol]["total_cost"] -= sell_vol * avg_cost

    result = []
    for symbol, data in symbol_data.items():
        vol = data["volume"]
        if vol > 0:
            avg_price = data["total_cost"] / vol
            result.append(
                {
                    "symbol": symbol,
                    "volume": vol,
                    "avg_price": round(avg_price, 2),
                }
            )

    return result if result else False


def get_quote(db):
    stocks = db.query(models.Stock).all()
    if not stocks:
        return False

    settrade_api = api.SetTradeSymbol()

    for stock in stocks:
        res = settrade_api.get_quote_symbol(stock.symbol)
        if not res:
            continue

        pbv = res.get("pbv", 1.0)
        eps = res.get("eps", 1.0)

        turnover = (
            db.query(models.Turnover)
            .filter(models.Turnover.symbol == stock.symbol)
            .first()
        )
        if not turnover:
            turnover = models.Turnover(
                symbol=stock.symbol,
                pbv=pbv,
                eps=eps,
            )
            db.add(turnover)
        else:
            turnover.pbv = pbv
            turnover.eps = eps

        db.commit()

    return True
