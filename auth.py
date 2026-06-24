import bcrypt
from schemas import Role
from jose import jwt,JWTError
from datetime import datetime, timedelta,timezone
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from db_connection import get_db
from db_models import Author

# ========== LOGGING ==========
import logging
logger = logging.getLogger(__name__)

# === Configuration ===
SECRET_KEY = "secret123321secretsecret123321"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ========== HASHING FUNCTIONS ==========
def hash_psw(inp_pw: str):
    logger.debug("Hashing password")
    pw_bites = inp_pw.encode("utf-8")
    hashed_pw = bcrypt.hashpw(pw_bites, bcrypt.gensalt())
    return hashed_pw.decode('utf-8')

def check_psw(inp_psw: str, stored_hash):
    logger.debug("Verifying password")
    pw_bites = inp_psw.encode("utf-8")
    stored_hash = stored_hash.encode("utf-8")
    is_valid = bcrypt.checkpw(pw_bites, stored_hash)
    logger.debug(f"Password verification result: {is_valid}")
    return is_valid

# ========== TOKEN FUNCTIONS ==========
def create_access_token(data: dict, expire_time_inp: timedelta = None) -> str:
    logger.debug("Creating access token")
    za_data = data.copy()
    if expire_time_inp:
        expire_time = datetime.now(timezone.utc) + expire_time_inp
    else:
        expire_time = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    za_data['exp'] = expire_time
    token = jwt.encode(za_data, SECRET_KEY, ALGORITHM)
    logger.debug("Access token created")
    return token

def verify_token(token: str) -> dict:
    logger.debug("Verifying token")
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug("Token verified successfully")
        return data
    except jwt.JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None

# ========== AUTHENTICATION FUNCTIONS ==========
def authenticate_author(email: str, password: str, db: Session):
    logger.debug(f"Authenticating user: {email}")
    
    author = db.query(Author).filter(Author.email == email).first()
    if not author:
        logger.warning(f"Authentication failed: email not found - {email}")
        return None
    
    if not check_psw(password, author.hashed_password):
        logger.warning(f"Authentication failed: wrong password - {email}")
        return None
    
    logger.info(f"Authentication successful: {email}")
    return author

def get_current_author(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    logger.debug("Extracting current user from token")
    
    data = verify_token(token)
    if data is None:
        logger.warning("Invalid token received")
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token credentials',
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    author_id = data['author_id']
    if author_id is None:
        logger.warning("Token missing author_id")
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token credentials',
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    author = db.query(Author).filter(Author.id == author_id).first()
    if author is None:
        logger.warning(f"Author not found for ID: {author_id}")
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token credentials',
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    logger.debug(f"Current user: {author.email}")
    return author

def require_admin(token: str = Depends(oauth2_scheme)):
    logger.debug("Checking admin permissions")
    data = verify_token(token)
    if data is None:
        logger.warning("Invalid token for admin check")
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token credentials',
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if data.get('role') != Role.ADMIN.value:
        logger.warning(f"User tried to access admin endpoint without admin role: {data.get('author_id')}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='you\'r not him bro')
    
    logger.debug("Admin permission granted")
    return True