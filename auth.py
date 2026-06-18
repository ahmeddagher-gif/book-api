import bcrypt
from schemas import Role
from jose import jwt,JWTError
from datetime import datetime, timedelta,timezone
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from db_connection import get_db
from db_models import Author
# === Configuration ===
SECRET_KEY = "secret123321secretsecret123321"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")#this is the endpoint where at the end the user gets the token(ticket) and uses it then in protected endpoints


#hashing functions
def hash_psw(inp_pw:str):
    pw_bites=inp_pw.encode("utf-8")
    hashed_pw=bcrypt.hashpw(pw_bites,bcrypt.gensalt())
    return hashed_pw.decode('utf-8')

def check_psw(inp_psw:str,stored_hash):
    pw_bites=inp_psw.encode("utf-8")
    stored_hash=stored_hash.encode("utf-8")
    is_valid=bcrypt.checkpw(pw_bites,stored_hash)
    return is_valid


#token functions
def create_access_token(data:dict,expire_time_inp:timedelta = None)->str:#takes data(dict) returns token(str)
    za_data=data.copy()
    if expire_time_inp:
        expire_time=datetime.now(timezone.utc)+ expire_time_inp
    else:
        expire_time=datetime.now(timezone.utc)+timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    za_data['exp']=expire_time
    token=jwt.encode(za_data,SECRET_KEY,ALGORITHM)
    return token

def verify_token(token:str)->dict:#takes token(str) return data(dict)
    try:
        data=jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        return data
    except jwt.JWTError:
        return None

#authentication functions:-

def authenticate_author(email:str,password:str,db:Session):
    author=db.query(Author).filter(Author.email==email).first()# you're here querying the database table 
    if not author:
        return None
    if not check_psw(password,author.hashed_password):#but here you're simply fetching the stored hashed password that's why it's author not Author
        return None
    return author 

def get_current_author(token:str=Depends(oauth2_scheme),db:Session=Depends(get_db)):
    data=verify_token(token)
    if data is None :
        raise HTTPException (
            status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token credentials',
            headers={"WWW-Authenticate": "Bearer"}
             )
    author_id=data['author_id']
    if author_id is None:#the id is already checked in the schema but this is defensive programming
        raise HTTPException (
            status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token credentials',#you could say the id isn't found but it's best you don't tell anyone your failure details in security so not just in details also in the http exception just say unauthorizd
            headers={"WWW-Authenticate": "Bearer"}
             )
    author=db.query(Author).filter(Author.id==author_id).first()
    if author is None:
        raise HTTPException (
            status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token credentials',#you could say the id isn't found but it's best you don't tell anyone your failure details in security so not just in details also in the http exception just say unauthorizd
            headers={"WWW-Authenticate": "Bearer"}
             )
    return author


def require_admin(token:str=Depends(oauth2_scheme)):
    data=verify_token(token)
    print("TOKEN DATA:", data)  # ← add this
    print("ROLE VALUE:", data.get('role'))
    print("EXPECTED:", Role.ADMIN.value)
    if data is None:
        raise HTTPException (
        status.HTTP_401_UNAUTHORIZED,
        detail='Invalid token credentials',
        headers={"WWW-Authenticate": "Bearer"}
        )
    #if data["role"]!=Role.ADMIN:
    if data.get('role')!=Role.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail='you\'r not him bro')
    
            






