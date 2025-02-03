from sqlalchemy import Column, Integer, String, Text, JSON, VARCHAR
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


class FormsTests(Base):
    __tablename__ = 'forms'

    form_id = Column(VARCHAR(24), primary_key=True)
    title = Column(Text, nullable=False)  # varchar(128)
    url = Column(Text, nullable=False)  # int(11)
    accesses = Column(JSON, nullable=True, default=None)  # varchar(50)
