from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from database import SessionLocal, engine
import models
import datetime
from datetime import date
from fastapi.middleware.cors import CORSMiddleware


SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

models.Base.metadata.create_all(bind=engine)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict, expires_delta: datetime.timedelta = None):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + (expires_delta or datetime.timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class AccountStatementCreate(BaseModel):
    date: date
    category: str
    type: str
    amount: float


@app.post("/expense/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.Users).filter(models.Users.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_pw = pwd_context.hash(user.password)
    new_user = models.Users(
        username=user.username,
        email=user.email,
        password=hashed_pw
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"msg": "User registered", "user_id": new_user.user_id}

@app.post("/token") 
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.Users).filter(models.Users.username == form_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not pwd_context.verify(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": str(user.user_id)})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/expense/dashboard")
def get_dashboard(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    statements = db.query(models.AccountStatements).filter(models.AccountStatements.user_id == int(user_id)).all()

    return [
        {
            "date": str(stmt.date),
            "category": stmt.category,
            "type": stmt.type,
            "amount": float(stmt.amount)
        }
        for stmt in statements
    ]

@app.post("/expense/dashboard")
def add_account_statement(
    data: AccountStatementCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(models.Users).filter(models.Users.user_id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_entry = models.AccountStatements(
        user_id=int(user_id),
        date=data.date,
        category=data.category,
        type=data.type,
        amount=data.amount
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)

    return {
        "message": "Account statement added successfully",
        "data": {
            "date": str(new_entry.date),
            "category": new_entry.category,
            "type": new_entry.type,
            "amount": float(new_entry.amount)
        }
    }

@app.get("expense/dashboard/statement/edit/{user_id}/{date}/{category}/{type}/{amount}")
def get_edit_statements(user_id: int, date: date, category: str, type: str, amount:float, db: Session = Depends(get_db)):
    statements = db.query(models.AccountStatements).filter(models.AccountStatements.user_id == user_id).filter(models.AccountStatements.category==category).filter(models.AccountStatements.date == date).filter(models.AccountStatements.amount==amount).filter(models.AccountStatements.type == type).all()

    if not statements:
        raise HTTPException(status_code=404, detail="No records found for the given user_id")

    for statement in statements:
        db.delete(statement)
    db.commit()
    return {
        "user_id":user_id,
        "date":date,
        "type":type,
        "amount":amount,
        "category":category
    }


@app.post("expense/dashboard/statement/edit/{user_id}/{date}/{category}/{type}/{amount}")
def post_edit_statements(user_id: int, date: date, category: str, type: str, amount:float, db: Session = Depends(get_db)):
    new_entry = models.AccountStatements(
        user_id=int(user_id),
        date=date,
        category=category,
        type=type,
        amount=amount
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return {
        "message": "Account statement added successfully",
        "data": {
            "date": str(new_entry.date),
            "category": new_entry.category,
            "type": new_entry.type,
            "amount": float(new_entry.amount)
        }
    }

@app.delete("expense/dashboard/statement/delete/{user_id}/{date}/{category}/{type}/{amount}")
def delete_statements(user_id: int, date: date, category: str, type: str, amount:float, db: Session = Depends(get_db)):
    
    statements = db.query(models.AccountStatements).filter(models.AccountStatements.user_id == user_id).filter(models.AccountStatements.category==category).filter(models.AccountStatements.date == date).filter(models.AccountStatements.amount==amount).filter(models.AccountStatements.type == type).all()

    if not statements:
        raise HTTPException(status_code=404, detail="No records found for the given user_id")

    for statement in statements:
        db.delete(statement)
    db.commit()

    return {"message": f"All records for user_id {user_id} have been deleted"}