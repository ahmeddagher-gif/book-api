from fastapi import FastAPI, Depends, HTTPException, status, Request, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List
import logging
import redis
import os
from dotenv import load_dotenv

# ========== ENVIRONMENT VARIABLES ==========
load_dotenv()

# ========== LOGGING ==========
from logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

# ========== DATABASE ==========
from db_connection import get_db, session_factory, engine
from db_models import base, book_model, Author

# ========== REDIS ==========
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
try:
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True, protocol=2)
except:
    # Fallback to direct connection
    r = redis.Redis(
        host='localhost',
        port=6379,
        decode_responses=True,
        protocol=2
    )

# ========== RATE LIMITER ==========
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# ========== LIFESPAN (Graceful Shutdown & Startup) ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ===== STARTUP =====
    logger.info("Application starting...")
    
    # Check database connection on startup
    try:
        with session_factory() as db:
            db.execute(text("SELECT 1"))
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
    
    # Check Redis connection on startup
    try:
        r.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise
    
    # Create database tables (if needed)
    try:
        base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise
    
    # ===== APP RUNS HERE =====
    yield
    
    # ===== SHUTDOWN =====
    logger.info("Application shutting down gracefully...")
    
    # Close Redis connection
    try:
        r.close()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis connection: {e}")
    
    logger.info("Application shut down successfully")

# ========== APP CREATION ==========
app = FastAPI(lifespan=lifespan)

# ========== EXCEPTION HANDLERS ==========
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ========== CORS ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "https://your-app.onrender.com",  # Replace with your Render URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== HEALTH CHECK ==========
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint for Render and monitoring.
    Checks database and Redis connections.
    """
    try:
        # Check database
        db.execute(text("SELECT 1"))
        
        # Check Redis
        r.ping()
        
        return {
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )

# ========== IMPORT YOUR FILES ==========
import my_funcs
import auth
from schemas import (
    book_create, za_response, book_update,
    Author_create, Author_update, Author_response,
    my_log_in, token_response
)
from datetime import timedelta

# ========== BOOK ENDPOINTS ==========
@app.get("/books", response_model=list[za_response])
@limiter.limit("60/minute")
def get_all_books(request: Request, skip: int = 0, limit: int = 2, db: Session = Depends(get_db)):
    logger.info(f"GET /books called with skip={skip}, limit={limit}")
    try:
        result = my_funcs.get_all_books(skip, limit, db)
        logger.info(f"Returned {len(result)} books")
        return result
    except Exception as e:
        logger.error(f"Error getting books: {e}", exc_info=True)
        raise

@app.get("/book/{book_id}", response_model=za_response)
@limiter.limit("60/minute")
def get_book_by_id(request: Request, book_id: int, db: Session = Depends(get_db)):
    logger.info(f"GET /book/{book_id} called")
    try:
        return my_funcs.get_book(db, book_id)
    except HTTPException as e:
        if e.status_code == 404:
            logger.warning(f"Book {book_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error getting book {book_id}: {e}", exc_info=True)
        raise

@app.post("/create-book", response_model=za_response, status_code=201)
@limiter.limit("10/minute")
async def create_book(request: Request, request_body: book_create, db: Session = Depends(get_db)):
    logger.info(f"POST /create-book called with title: {request_body.book_name}")
    try:
        new_book = my_funcs.create_book(request_body, db)
        await my_funcs.broadcast(new_book.book_name)
        logger.info(f"Book created: {new_book.book_name}")
        return new_book
    except Exception as e:
        logger.error(f"Error creating book: {e}", exc_info=True)
        raise

@app.put("/update-book/{book_id}", response_model=za_response)
@limiter.limit("10/minute")
def update_book(request: Request, book_id: int, request_body: book_update, db: Session = Depends(get_db)):
    logger.info(f"PUT /update-book/{book_id} called")
    try:
        result = my_funcs.update_book(db, request_body, book_id)
        logger.info(f"Book {book_id} updated successfully")
        return result
    except HTTPException as e:
        if e.status_code == 404:
            logger.warning(f"Book {book_id} not found for update")
        raise
    except Exception as e:
        logger.error(f"Error updating book {book_id}: {e}", exc_info=True)
        raise

@app.delete("/delete-book/{book_id}", status_code=204)
@limiter.limit("5/minute")
def delete_book(request: Request, book_id: int, db: Session = Depends(get_db)):
    logger.info(f"DELETE /delete-book/{book_id} called")
    try:
        my_funcs.delete_book(db, book_id)
        logger.info(f"Book {book_id} deleted successfully")
        return
    except HTTPException as e:
        if e.status_code == 404:
            logger.warning(f"Book {book_id} not found for deletion")
        raise
    except Exception as e:
        logger.error(f"Error deleting book {book_id}: {e}", exc_info=True)
        raise

# ========== AUTHOR ENDPOINTS ==========
@app.get("/authors", response_model=list[Author_response])
@limiter.limit("60/minute")
def get_all_authors(request: Request, skip: int = 0, limit: int = 2, db: Session = Depends(get_db)):
    logger.info(f"GET /authors called with skip={skip}, limit={limit}")
    try:
        result = my_funcs.get_all_authors(skip, limit, db)
        logger.info(f"Returned {len(result)} authors")
        return result
    except Exception as e:
        logger.error(f"Error getting authors: {e}", exc_info=True)
        raise

@app.get("/author/{author_id}", response_model=Author_response)
@limiter.limit("60/minute")
def get_author_by_id(request: Request, author_id: int, db: Session = Depends(get_db)):
    logger.info(f"GET /author/{author_id} called")
    try:
        return my_funcs.get_author_by_id(db, author_id)
    except HTTPException as e:
        if e.status_code == 404:
            logger.warning(f"Author {author_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error getting author {author_id}: {e}", exc_info=True)
        raise

@app.post("/create-author", response_model=Author_response, status_code=201)
@limiter.limit("10/minute")
def create_author(request: Request, request_body: Author_create, db: Session = Depends(get_db)):
    logger.info(f"POST /create-author called for email: {request_body.email}")
    
    if my_funcs.check_author_exists(request_body, db):
        logger.warning(f"Attempt to create existing author: {request_body.email}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="author already exists bro ")
    
    try:
        author = my_funcs.create_author(db, request_body)
        logger.info(f"Author created successfully: {author.email}")
        return author
    except Exception as e:
        logger.error(f"Error creating author {request_body.email}: {e}", exc_info=True)
        raise

@app.post("/create-author-no-return", status_code=201)
@limiter.limit("10/minute")
def create_author_no_return(
    background_tasks: BackgroundTasks,
    request: Request,
    request_body: Author_create,
    db: Session = Depends(get_db)
):
    logger.info(f"POST /create-author-no-return called for email: {request_body.email}")
    
    if my_funcs.check_author_exists(request_body, db):
        logger.warning(f"Attempt to create existing author: {request_body.email}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="author already exists bro ")
    
    background_tasks.add_task(my_funcs.create_author, db, request_body)
    logger.info(f"Author creation task added to background for: {request_body.email}")
    return "welcome author , you're now an author and i will not return anything sorry "

@app.put("/update-author/{author_id}", response_model=Author_response)
@limiter.limit("10/minute")
def update_author(request: Request, author_id: int, request_body: Author_update, db: Session = Depends(get_db)):
    logger.info(f"PUT /update-author/{author_id} called")
    try:
        result = my_funcs.update_author(db, request_body, author_id)
        logger.info(f"Author {author_id} updated successfully")
        return result
    except HTTPException as e:
        if e.status_code == 404:
            logger.warning(f"Author {author_id} not found for update")
        raise
    except Exception as e:
        logger.error(f"Error updating author {author_id}: {e}", exc_info=True)
        raise

@app.delete("/delete-author/{author_id}", status_code=204)
@limiter.limit("5/minute")
def delete_author(request: Request, author_id: int, db: Session = Depends(get_db)):
    logger.info(f"DELETE /delete-author/{author_id} called")
    try:
        my_funcs.delete_author(db, author_id)
        logger.info(f"Author {author_id} deleted successfully")
        return
    except HTTPException as e:
        if e.status_code == 404:
            logger.warning(f"Author {author_id} not found for deletion")
        raise
    except Exception as e:
        logger.error(f"Error deleting author {author_id}: {e}", exc_info=True)
        raise

# ========== RELATIONSHIP ENDPOINTS ==========
@app.get("/author-books/{author_id}", response_model=list[za_response])
@limiter.limit("60/minute")
def get_author_books(request: Request, author_id: int, db: Session = Depends(get_db)):
    logger.info(f"GET /author-books/{author_id} called")
    try:
        author = my_funcs.get_author_by_id(db, author_id)
        return author.books
    except Exception as e:
        logger.error(f"Error getting books for author {author_id}: {e}", exc_info=True)
        raise

@app.get("/book-author/{book_id}", response_model=Author_response)
@limiter.limit("60/minute")
def get_book_author(request: Request, book_id: int, db: Session = Depends(get_db)):
    logger.info(f"GET /book-author/{book_id} called")
    try:
        book = my_funcs.get_book(db, book_id)
        return book.author
    except Exception as e:
        logger.error(f"Error getting author for book {book_id}: {e}", exc_info=True)
        raise

# ========== AUTHENTICATION ENDPOINTS ==========
@app.post("/login")
@limiter.limit("5/minute")
def log_in(request: Request, log_in_data: my_log_in, db: Session = Depends(get_db)) -> token_response:
    logger.info(f"Login attempt for email: {log_in_data.email}")
    
    author = auth.authenticate_author(log_in_data.email, log_in_data.password, db)
    if not author:
        logger.warning(f"Failed login attempt for email: {log_in_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="wrong email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    expiry_time = timedelta(minutes=30)
    data = {"author_id": author.id}
    token = auth.create_access_token(data, expiry_time)
    
    logger.info(f"Successful login for email: {log_in_data.email}")
    return {"access_token": token, "token_type": "bearer"}

# ========== PROTECTED ENDPOINTS ==========
@app.get("/my-profile", response_model=Author_response)
@limiter.limit("60/minute")
def get_profile(request: Request, author: Author = Depends(auth.get_current_author), db: Session = Depends(get_db)):
    logger.info(f"GET /my-profile called for user: {author.email}")
    return author

@app.get("/my-books", response_model=list[za_response])
@limiter.limit("60/minute")
def get_my_books(request: Request, author: Author = Depends(auth.get_current_author), db: Session = Depends(get_db)):
    logger.info(f"GET /my-books called for user: {author.email}")
    return author.books

# ========== ADMIN ENDPOINTS ==========
@app.delete('/delete-other-author/{author_id}', status_code=204)
@limiter.limit("3/minute")
def delete_other_author(request: Request, author_id: int, _=Depends(auth.require_admin), db: Session = Depends(get_db)):
    logger.info(f"DELETE /delete-other-author/{author_id} called by admin")
    try:
        my_funcs.delete_author(db, author_id)
        logger.info(f"Author {author_id} deleted by admin")
        return
    except HTTPException as e:
        if e.status_code == 404:
            logger.warning(f"Author {author_id} not found for admin deletion")
        raise
    except Exception as e:
        logger.error(f"Error deleting author {author_id} by admin: {e}", exc_info=True)
        raise

# ========== WEBSOCKET ==========
connections: List[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logger.info("New WebSocket connection attempt")
    await websocket.accept()
    connections.append(websocket)
    logger.info(f"WebSocket connection accepted. Total connections: {len(connections)}")
    
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"WebSocket received: {data}")
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(connections)}")