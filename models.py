#encoding: utf-8

import os
import datetime

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relation, sessionmaker
 
import config

BaseModel = declarative_base()


class SmsMessage(BaseModel):
    __tablename__ = 'sms_messages'
    id = Column(Integer, primary_key=True)
    arrived_time = Column(DateTime, nullable=False)
    mobile = Column(String(32), nullable=True)
    content = Column(String(256), nullable=True)

    def __repr__(self):
        return "SmsMessage(%r, %r, %r)" % (self.arrived_time, self.mobile, self.content)


class TradeLead(BaseModel):
    __tablename__ = 'trade_leads'
    id = Column(Integer, primary_key=True)
    created_time = Column(DateTime, nullable=False)
    exchange_to_buy = Column(String(32), nullable=False)
    exchange_to_sell = Column(String(32), nullable=False)
    buy_price = Column(Float, nullable=False)
    sell_price = Column(Float, nullable=False)
 
    def __init__(self, buy_exchange, buy_price, sell_exchange, sell_price):
        self.created_time = datetime.datetime.now()
        self.exchange_to_buy = buy_exchange
        self.buy_price = buy_price
        self.exchange_to_sell = sell_exchange
        self.sell_price = sell_price

    @staticmethod
    def last():
        session = Session()
        o = session.query(TradeLead).order_by(TradeLead.created_time.desc()).first()
        return o

 
class Order(BaseModel):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    created_time = Column(DateTime, nullable=False)
    sold_time = Column(DateTime, nullable=True)
    bought_time = Column(DateTime, nullable=True)
    is_bought = Column(Boolean, nullable=False)
    is_sold = Column(Boolean, nullable=False)
    exchange_to_buy = Column(String(32), nullable=False)
    exchange_to_sell = Column(String(32), nullable=False)
    buy_price = Column(Float, nullable=False)
    sell_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    state = Column(Enum('processing', 'done', 'cancel', 'except'), nullable=False)
    #director = relation("Director", backref='movies', lazy=False)
 
    def __init__(self, buy_exchange, buy_price, sell_exchange, sell_price, qty):
        self.created_time = datetime.datetime.now()
        self.is_sold = False
        self.is_bought = False        
        self.exchange_to_buy = buy_exchange
        self.buy_price = buy_price
        self.exchange_to_sell = sell_exchange
        self.sell_price = sell_price
        self.quantity = qty
        self.state = 'processing'

    def __repr__(self):
        return "Order(%r, %r, %r, %r, %r, %r)" % (self.id, self.created_time, self.buy_price, self.sell_price, self.quantity, self.state)

    @staticmethod
    def last():
        session = Session()
        o = session.query(Order).order_by(Order.id.desc()).first()
        return o
 
db_path = os.path.join(config.configuration['data_path'], 'brickmover.db')
engine = create_engine('sqlite:///' + db_path)
BaseModel.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

'''
session = Session()
 
m1 = Movie("Star Trek", 2009)
m1.director = Director("JJ Abrams")
 
d2 = Director("George Lucas")
d2.movies = [Movie("Star Wars", 1977), Movie("THX 1138", 1971)]
 
try:
    session.add(m1)
    session.add(d2)
    session.commit()
except:
    session.rollback()

alldata = session.query(Movie).all()
for somedata in alldata:
    print somedata
'''    
