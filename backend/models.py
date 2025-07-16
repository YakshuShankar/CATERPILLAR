from database import Base
from sqlalchemy import Column, Integer, String, ForeignKey,Numeric,CheckConstraint,Date

class Users(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, index=True, nullable=False)
    username = Column(String(100), nullable=False,index=True)
    email = Column(String(100), nullable=False)
    password=Column(String(100),nullable=False)

class AccountStatements(Base):
    __tablename__='accountstatements'

    id = Column(Integer, primary_key=True, index=True)
    user_id=Column(Integer, ForeignKey('users.user_id'))
    date=Column(Date,nullable=False)
    category=Column(String(50))
    type=Column(String(50))
    amount=Column(Numeric(10,2))
    __table_args__ = (
        CheckConstraint("type IN ('Income','Expenditure')", name="Expense_Type"),
    )