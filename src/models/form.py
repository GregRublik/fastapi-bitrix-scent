from sqlalchemy import Column, Text, JSON, VARCHAR


from src.db.database import Base

class FormsTests(Base):
    __tablename__ = 'forms'

    form_id = Column(VARCHAR(24), primary_key=True)
    title = Column(Text, nullable=False)  # varchar(128)
    url = Column(Text, nullable=False)  # int(11)
    accesses = Column(JSON, nullable=True, default=None)  # varchar(50)