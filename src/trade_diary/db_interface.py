
import re
from sqlalchemy import create_engine, Column, Integer, String, Date, Numeric, ForeignKey, Boolean, select, CHAR 
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, date
import numpy as np
import pandas as pd

import logging
from sqlalchemy import func


from .utility_functions import get_entry_adjustment_details, extract_financial_year



Base = declarative_base()


class   Trade(Base):
    __tablename__ = 'trades'

    trade_id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False)
    initial_entry_date = Column(Date, nullable=False)
    setup = Column(String, nullable=False)
    trade_closed = Column(CHAR(1), nullable=False, default='N')
    entries = relationship("Entry", back_populates="trades", cascade="all, delete-orphan")
    exits = relationship("Exits", back_populates="trades", cascade="all, delete-orphan")
    financial_year = Column(String, nullable=False)

class Entry(Base):
    __tablename__ = 'entries'
    entry_id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, ForeignKey('trades.trade_id'), nullable=False)
    entry_date = Column(Date, nullable=False)
    entry_price = Column(Numeric(10, 4), nullable=False)
    quantity = Column(Integer, nullable=False)
    remaining_quantity = Column(Integer, nullable=False)
    risk_percentage = Column(Numeric(5, 2), nullable=False)  
    entry_type = Column(String, nullable=True)
    stop_loss = Column(Numeric(10, 4), nullable=False)
    exit_amount = Column(Numeric(10, 4), nullable=False, default=0)
    charges = Column(Numeric(10, 2), nullable=False, default=0)
    trades = relationship("Trade", back_populates="entries")

class Exits(Base):
    __tablename__ = 'exits'
    exit_id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, ForeignKey('trades.trade_id'), nullable=False)
    exit_date = Column(Date, nullable=False)
    exit_price = Column(Numeric(10, 4), nullable=False)
    quantity = Column(Integer, nullable=False)
    exit_type = Column(String, nullable=True)
    exit_reason = Column(String, nullable=True)
    trades = relationship("Trade", back_populates="exits")



_engine = None
_SessionMaker = None

def get_engine():
    logging.debug("Get Engine")
    global _engine
    return _engine

def get_session():
    global _SessionMaker
    engine = get_engine()
    if _SessionMaker is None:
        _SessionMaker = sessionmaker(bind=engine)
        logging.info(f"SessionMaker created")
    return _SessionMaker()

def init_db(db_path):
    logging.info(f"Database Initialized")
    if db_path is None :
        logging.error("Database path is None")
        raise ValueError("Database path is None")
    global _engine
    if _engine is None:
        _engine = create_engine(db_path, echo=False)
        logging.info(f"Database Engine created with path: {db_path}")
    Base.metadata.create_all(_engine)
    return _engine


def insert_trade(symbol, entry_price, quantity, entry_date, risk_percentage, stop_loss, setup, entry_type=None):
    logging.debug(f"Insert Trade")
    session = get_session()

    try:
        financial_year = extract_financial_year(entry_date)
        new_trade = Trade(symbol=symbol.upper(), 
                          initial_entry_date=entry_date, 
                          setup=setup.upper(), financial_year=financial_year)
        session.add(new_trade)
        session.flush()
        entry = Entry(
            trade_id=new_trade.trade_id,    
            entry_date=new_trade.initial_entry_date,
            entry_price=entry_price,
            quantity=quantity,
            remaining_quantity=quantity,
            risk_percentage=risk_percentage,
            entry_type=entry_type,
            stop_loss=stop_loss,
            exit_amount=0,
            charges=0
        )
        
        session.add(entry)
        session.commit()
        logging.info(f"Trade inserted successfully with trade_id: {new_trade.trade_id}")
        return new_trade.trade_id
    except Exception as e:
        session.rollback()
        logging.error(f"Error inserting trade: {e}")
        return None
    finally:
        session.close()

def delete_trade(trade_id):
    logging.debug(f"Delete Trade")
    session = get_session()

    try :
        trade = session.query(Trade).filter_by(trade_id=trade_id).first()
        if not trade :
            logging.error(f"Trade with trade_id {trade_id} not found")
            return False
        session.delete(trade)
        session.commit()
        logging.info(f"Trade {trade_id} Deleted succesfully")
        return True
    except  Exception as e :
        session.rollback()
        logging.error(f'Error while deleting Trade {trade_id}')
        return False
    finally:
        session.close()
        


def insert_entry(trade_id, entry_price, quantity, entry_date, risk_percentage, entry_type=None, stop_loss=None):
    logging.debug(f"Insert Entry")
    session = get_session()

    try :
        entry = Entry(
            trade_id=trade_id,
            entry_date=entry_date,
            entry_price=entry_price,
            quantity=quantity,
            remaining_quantity=quantity,
            risk_percentage=risk_percentage,
            entry_type=entry_type,
            stop_loss=stop_loss,
            exit_amount=0,
            charges=0
        )
        session.add(entry)
        session.commit()
        logging.info(f"Entry inserted successfully for trade_id: {trade_id}")
        return entry.trade_id
    except Exception as e:
        session.rollback()
        logging.error(f"Error inserting entry: {e}")
        return None
    finally:
        session.close()

def insert_exit(trade_id, exit_price, quantity, exit_date, exit_type):
    logging.debug(f"Exit Position - {trade_id}, {quantity}, {exit_price}, {exit_date}, {exit_type}")
    engine = get_engine()
    session = get_session()

    try:

        
        entries_df = pd.read_sql(
            select(Entry).where(Entry.trade_id == trade_id).where(Entry.remaining_quantity > 0),
            engine
        )

        entry_adjustment_details = get_entry_adjustment_details(entries_df, exit_date, quantity, exit_price)

        exit_record = Exits(
            trade_id=trade_id,
            exit_date=exit_date,
            quantity=quantity,
            exit_price=exit_price,
            exit_type=exit_type,
            exit_reason=''
        )
        session.add(exit_record)

        for entry in entry_adjustment_details:
            
            entry_id, remaining_quantity, exit_amount, old_charges, exit_price, exit_quantity, total_charges = entry
            entry_record = session.query(Entry).filter_by(entry_id=entry_id).first()
            entry_record.remaining_quantity = remaining_quantity - exit_quantity
            entry_record.exit_amount = exit_amount + (exit_price * exit_quantity)
            entry_record.charges = old_charges + total_charges

        session.flush()

        total_remaining_quantity = session.query(func.sum(Entry.remaining_quantity)).filter_by(trade_id=trade_id).scalar()

        if total_remaining_quantity == 0:
            trade = session.query(Trade).filter_by(trade_id=trade_id).first()
            if trade:
                trade.trade_closed = 'Y'
                
                logging.info(f"Trade {trade_id} marked as closed.")

        logging.info(f"Exit position recorded for trade_id: {trade_id}")
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        logging.error(f"Error exiting position: {e}")
        return False
    finally:
        session.close()



def get_all_trades_and_entries(show_trades = 'all', financial_year=None, filter_conditions=None):   
    logging.debug(f"Get All Trades and Entries - Show Only Open: {show_trades}, Financial Year: {financial_year}")
    if financial_year is None:
        financial_year = extract_financial_year(date.today())
    engine = get_engine()
    try:
        exits_subq = (
            select(
            Exits.trade_id,
            func.sum(Exits.quantity).label("total_exit_quantity"),
            func.count(Exits.exit_id).label("num_exits"),
            func.sum(Exits.exit_price * Exits.quantity).label("total_sell_amount"),
            func.max(Exits.exit_date).label("last_exit_date")
            )
            .group_by(Exits.trade_id)
            .subquery()
        )

        entries_subq = (
            select(
            Entry.trade_id,
            func.sum(Entry.quantity).label("total_entry_quantity"),
            func.sum(Entry.remaining_quantity).label("total_remaining_quantity"),
            func.sum(Entry.charges).label("total_charges"),
            func.sum(Entry.risk_percentage).label("total_risk_percentage"),
            func.count(Entry.entry_id).label("num_entries"),
            func.sum(Entry.entry_price * Entry.quantity).label("total_buy_amount"),
            )
            .group_by(Entry.trade_id)
            .subquery()
        )

        stmt = (
            select(
            Trade,
            func.coalesce(entries_subq.c.total_buy_amount, 0).label("total_buy_amount"),
            func.coalesce(entries_subq.c.total_entry_quantity, 0).label("total_quantity"),
            func.coalesce(entries_subq.c.total_remaining_quantity, 0).label("total_open_position"),
            entries_subq.c.num_entries,
            entries_subq.c.total_risk_percentage,
            func.coalesce(entries_subq.c.total_charges, 0).label("total_charges"),
            func.coalesce(exits_subq.c.num_exits, 0).label("num_exits"),
            func.coalesce(exits_subq.c.total_sell_amount, 0).label("total_sell_amount"),
            func.coalesce(exits_subq.c.last_exit_date, None).label("last_exit_date")
            )
            .outerjoin(entries_subq, Trade.trade_id == entries_subq.c.trade_id)
            .outerjoin(exits_subq, Trade.trade_id == exits_subq.c.trade_id)
            .where(Trade.financial_year == financial_year)
            .group_by(Trade.trade_id)
            .order_by(Trade.initial_entry_date.desc())
        )

        if show_trades == 'open':
            stmt = stmt.where(Trade.trade_closed == 'N')
        elif show_trades == 'closed':
            stmt = stmt.where(Trade.trade_closed == 'Y')

        if filter_conditions :
            for filter_col, condition in filter_conditions.items():
                if filter_col == 'initial_entry_date':
                    if condition[0] == 'inRange':
                        stmt = stmt.where(getattr(Trade, filter_col).between(condition[1], condition[2]))
                    elif condition[0] == 'equals':
                        stmt = stmt.where(getattr(Trade, filter_col) == condition[1])
                    elif condition[0] == 'lessThan':
                        stmt = stmt.where(getattr(Trade, filter_col) < condition[1])
                    elif condition[0] == 'greaterThan':
                        stmt = stmt.where(getattr(Trade, filter_col) > condition[1])
                

        trades = pd.read_sql(stmt, engine)
        print("Trades DataFrame:", len(trades))

        if trades.empty:
            logging.info("No trades found for the given criteria.")
            return None
        
        logging.info(f"Fetched {len(trades)} trades from the database.")
        return trades 
    except Exception as e:
        logging.error(f"Error fetching trades: {e}")
        return None

def get_entries(trade_id):
    logging.debug(f"Get All Entries for Trade ID: {trade_id}")
    session = get_session()

    try:
        entries = session.query(Entry).filter_by(trade_id=trade_id).all()
        return entries
    except Exception as e:
        logging.error(f"Error fetching entries for trade_id {trade_id}: {e}")
        return []
    finally:
        session.close()

def get_exits(trade_id):
    logging.debug(f"Get All Exits for Trade ID: {trade_id}")
    session = get_session()

    try:
        exits = session.query(Exits).filter_by(trade_id=trade_id).all()
        return exits
    except Exception as e:
        logging.error(f"Error fetching exits for trade_id {trade_id}: {e}")
        return []
    finally:
        session.close()

def get_all_financial_years():
    logging.debug(f"Get All Financial Years")
    session = get_session()

    try:
        stmt = select(Trade.financial_year).distinct().order_by(Trade.financial_year.desc())
        result = session.execute(stmt).scalars().all()
        return result
    except Exception as e:
        logging.error(f"Error fetching financial years: {e}")
        return []
    finally:
        session.close()

def get_all_entries(financial_year='all'):
    logging.debug(f"get_all_entries: Get All Entries for Financial Year: {financial_year}")
    engine = get_engine()
    try:
        if financial_year == 'all' or financial_year is None:
            stmt = select(Entry).join(Trade).where(Trade.trade_closed=='Y')
        else:
            stmt = select(Entry).join(Trade).where(Trade.financial_year == financial_year).where(Trade.trade_closed=='Y')
        entries = pd.read_sql(stmt, engine)
        return entries
    except Exception as e:
        logging.error(f"Error fetching entries: {e}")
        return None
    
def get_all_exits(financial_year='all'):
    logging.debug(f"get_all_exits: Get All Exits for Financial Year: {financial_year}")
    engine = get_engine()
    try:
        if financial_year == 'all' or financial_year is None:
            stmt = select(Exits).join(Trade).where(Trade.trade_closed=='Y')
        else:
            stmt = select(Exits).join(Trade).where(Trade.financial_year == financial_year)
        exits = pd.read_sql(stmt, engine)
        return exits
    except Exception as e:
        logging.error(f"Error fetching exits: {e}")
        return None

    
def get_all_trades(financial_year='all'):
    logging.debug(f"get_all_trades: Get All Trades for Financial Year: {financial_year}")
    engine = get_engine()
    try:
        if financial_year == 'all' or financial_year is None:
            stmt = select(Trade).where(Trade.trade_closed=='Y')
        else:
            stmt = select(Trade).where(Trade.financial_year == financial_year).where(Trade.trade_closed=='Y')
        trades = pd.read_sql(stmt, engine)
        return trades
    except Exception as e:
        logging.error(f"Error fetching trades: {e}")
        return None 


def insert_test_data():
    logging.debug(f"Insert Test Data")
    session = get_session()

    try:
        trade_id1 = insert_trade(symbol="AAPL", entry_date=datetime(2025, 7, 22), entry_price=150.00, quantity=10, risk_percentage=1.0, setup="Breakout", entry_type="Market", stop_loss=145.00)
        insert_entry(trade_id=trade_id1, entry_price=180.00, quantity=10, risk_percentage=0.5, entry_date=datetime(2025, 7, 24), entry_type="Market", stop_loss=145.00)
        insert_exit(trade_id=trade_id1, exit_price=200.00, quantity=20, exit_date=datetime(2025, 7, 26), exit_type="Market")

        trade_id2 = insert_trade(symbol="GOOGL", entry_date=datetime(2025, 7, 23), entry_price=2800.00, quantity=100, risk_percentage=1.0, setup="Reversal", entry_type="Limit", stop_loss=2750.00)
        insert_entry(trade_id=trade_id2, entry_price=2800.00, quantity=20, risk_percentage=1.0, entry_date=datetime(2025, 7, 23), entry_type="Limit", stop_loss=2750.00)
        insert_exit(trade_id=trade_id2, exit_price=4000.00, quantity=50, exit_date=datetime(2025, 7, 27), exit_type="Limit")
        insert_exit(trade_id=trade_id2, exit_price=2900.00, quantity=70, exit_date=datetime(2025, 7, 30), exit_type="Limit")


        trade_id3 = insert_trade(symbol="AMZN", entry_date=datetime(2025, 7, 24), entry_price=3400.00, quantity=20, risk_percentage=1.0, setup="Trend", entry_type="Market", stop_loss=3350.00)
        insert_entry(trade_id=trade_id3, entry_price=3400.00, quantity=10, risk_percentage=2.0, entry_date=datetime(2025, 8, 1), entry_type="Market", stop_loss=3350.00)
        insert_exit(trade_id=trade_id3, exit_price=2500.00, quantity=30, exit_date=datetime(2025, 8, 2), exit_type="Market")


        trade_id4 = insert_trade(symbol="MSFT", entry_date=datetime(2025, 7, 25), entry_price=300.00, quantity=1000, risk_percentage=1.0, setup="Breakout", entry_type="Market", stop_loss=295.00)
        insert_entry(trade_id=trade_id4, entry_price=400.00, quantity=1000, risk_percentage=2.0, entry_date=datetime(2025, 8, 1), entry_type="Market", stop_loss=300.00)
        insert_exit(trade_id=trade_id4, exit_price=350.00, quantity=1000, exit_date=datetime(2025, 8, 2), exit_type="Market")
        insert_exit(trade_id=trade_id4, exit_price=350.00, quantity=1000, exit_date=datetime(2025, 8, 10), exit_type="Market")


        trade_id5 = insert_trade(symbol="TSLA", entry_date=datetime(2025, 7, 21), entry_price=700.00, quantity=12, risk_percentage=1.0, setup="Pullback", entry_type="Market", stop_loss=690.00)
        insert_entry(trade_id=trade_id5, entry_price=700.00, quantity=12, risk_percentage=1.0, entry_date=datetime(2025, 7, 21), entry_type="Market", stop_loss=690.00)
        insert_exit(trade_id=trade_id5, exit_price=800.00, quantity=12, exit_date=datetime(2025, 7, 22), exit_type="Market")
        insert_exit(trade_id=trade_id5, exit_price=800.00, quantity=6, exit_date=datetime(2025, 7, 22), exit_type="Market")

        trade_id6 = insert_trade(symbol="ACC", entry_date=datetime(2023, 7, 21), entry_price=700.00, quantity=12, risk_percentage=1.0, setup="Pullback", entry_type="Market", stop_loss=690.00)
        trade_id7 = insert_trade(symbol="INFY", entry_date=datetime(2023, 2, 21), entry_price=700.00, quantity=12, risk_percentage=1.0, setup="Pullback", entry_type="Market", stop_loss=690.00)
        
        session.commit()


        logging.info("Test data inserted successfully")
    except Exception as e:
        session.rollback()
        logging.error(f"Error inserting test data: {e}")
    finally:
        session.close()
    
