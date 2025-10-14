# import yfinance as yf
# def fetch_current_prices(symbols):
#     tickers = " ".join(symbols.unique())
#     try :
#         data = yf.download(tickers=tickers, period="1d", interval="1d", progress=False,keepna=True)
#     except Exception as e:
#         logging.error(f"Error fetching data from Yahoo Finance: {e}")
#         return pd.Series(index = symbols)
#     if data.empty:
#         return pd.Series(index = symbols)

#     prices = pd.Series(index=symbols, dtype=float)
#     for symbol in symbols:
#         try:
#             # Get the last available close price
#             last_price = data['Close'][symbol].dropna().iloc[-1]
#             prices[symbol] = last_price
#         except Exception:
#             prices[symbol] = None
#     return prices.round(2)

import numpy as np
import pandas as pd
from datetime import datetime


charges = {
    "brokerage": {"intraday": 0.0003, "delivery": 0},
    "stt": {"intraday": 0.00025, "delivery": 0.001},
    "transaction_tax": {"intraday": 0.0000307, "delivery": 0.0000307},
    "sebi_charges": {"intraday": 10 / 10000000, "delivery": 10 / 10000000},
    "stamp_duty": {"intraday": 0.00003, "delivery": 0.00015},
    "gst": 0.18,
}


def calculate_charges(entry_date, exit_date, buy_amount, sell_amount):
    trade_type = "intraday" if entry_date == exit_date else "delivery"
    turnover = buy_amount + sell_amount

    brokerage = min(charges["brokerage"][trade_type] * buy_amount, 20) + min(
        charges["brokerage"][trade_type] * sell_amount, 20
    )
    stt = (
        charges["stt"][trade_type] * sell_amount
        if trade_type == "intraday"
        else charges["stt"][trade_type] * turnover
    )
    transaction_tax = (
        charges["transaction_tax"][trade_type] * buy_amount
        + charges["transaction_tax"][trade_type] * sell_amount
    )
    sebi_charges = charges["sebi_charges"][trade_type] * turnover
    stamp_duty = charges["stamp_duty"][trade_type] * buy_amount
    gst = (brokerage + transaction_tax + sebi_charges) * charges["gst"]
    dp_charges = 15.34 if trade_type == "delivery" else 0

    total_charges = (
        brokerage + stt + transaction_tax + sebi_charges + stamp_duty + gst + dp_charges
    )
    # print(f"Turnover: {turnover}, buy_amount: {buy_amount}, sell_amount: {sell_amount}")
    # print(f"brokerage: {brokerage}, stt: {stt}, transaction_tax: {transaction_tax}, sebi_charges: {sebi_charges}, stamp_duty: {stamp_duty}, gst: {gst}, total_charges: {total_charges}")
    return total_charges


def get_entry_adjustment_details(entries, exit_date, exit_quantity, exit_price):
    entries = entries.sort_values(by="entry_date", ascending=False)
    adjust_entry_details = []
    remaining_exit_quantity = exit_quantity

    for index, row in entries.iterrows():
        entry_id = row["entry_id"]
        entry_date = row["entry_date"]
        entry_quantity = row["quantity"]
        remaining_quantity = row["remaining_quantity"]
        entry_price = row["entry_price"]
        exit_amount = row["exit_amount"]
        old_charges = row["charges"]
        considered_qty = min(remaining_quantity, remaining_exit_quantity)
        remaining_exit_quantity -= considered_qty

        buy_amount = considered_qty * entry_price
        sell_amount = considered_qty * exit_price

        total_charges = calculate_charges(
            entry_date=entry_date,
            exit_date=exit_date,
            buy_amount=buy_amount,
            sell_amount=sell_amount,
        )

        adjust_entry_details.append(
            (
                entry_id,
                remaining_quantity,
                exit_amount,
                old_charges,
                exit_price,
                considered_qty,
                total_charges,
            )
        )
        if remaining_exit_quantity <= 0:
            break
    return adjust_entry_details


def add_additional_columns(trades):
    if trades is None or trades.empty:
        return trades

    trades.index = trades["symbol"]
    trades["avg_entry_price"] = (
        trades["total_buy_amount"] / trades["total_quantity"]
    ).round(2)
    trades["days_held"] = np.where(
        trades["total_open_position"] > 0,
        (datetime.now() - pd.to_datetime(trades["initial_entry_date"])).dt.days,
        (
            pd.to_datetime(trades["last_exit_date"])
            - pd.to_datetime(trades["initial_entry_date"])
        ).dt.days,
    )
    trades["status"] = np.where(trades["total_open_position"] > 0, "Open", "Closed")

    # trades['initial_entry_date'] = pd.to_datetime(trades['initial_entry_date']).dt.strftime('%Y-%m-%d')

    # to fetch current price from yahoo finance
    # current_close = fetch_current_prices(trades['symbol']).rename('current_close')
    # trades = trades.join(current_close)

    return trades


def extract_financial_year(date):
    if date.month >= 4:
        return f"{date.year}-{date.year + 1}"
    else:
        return f"{date.year - 1}-{date.year}"
