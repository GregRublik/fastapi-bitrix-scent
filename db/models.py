from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class BitrixAuth(Base):
    __tablename__ = 'bitrix_auth'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name_app = Column(String(128), nullable=False)  # varchar(128)
    owner = Column(Integer, nullable=False)           # int(11)
    client_secret = Column(String(50), nullable=False)  # varchar(50)
    client_id = Column(String(128), nullable=False)   # varchar(128)
    access_token = Column(String(256), nullable=False)  # varchar(256)
    refresh_token = Column(String(256), nullable=False)  # varchar(256)
