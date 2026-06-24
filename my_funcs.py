import main
import redis
import json
from db_models import book_model, Author
from schemas import Author_create, Author_update, book_create, book_update, my_log_in, za_response
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import auth
import os
import time
from dotenv import load_dotenv

# ========== LOGGING ==========
import logging
logger = logging.getLogger(__name__)

# ========== ENV SETUP ==========
load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# ========== BOOK CRUD FUNCTIONS ==========
def get_all_books(skip, limit, db: Session):
    logger.debug(f"Getting all books with skip={skip}, limit={limit}")
    books = db.query(book_model).order_by(book_model.id).offset(skip).limit(limit).all()
    logger.debug(f"Returning {len(books)} books")
    return books

def get_book(db: Session, book_id: int):
    start_time = time.time()
    logger.debug(f"Getting book with ID: {book_id}")
    
    cache_key = f'book:{book_id}'
    cached_book = r.get(cache_key)

    if cached_book:  # cache hit
        elapsed = time.time() - start_time
        logger.debug(f"Book {book_id} served from cache in {elapsed:.4f}s")
        return json.loads(cached_book)
    
    book = db.query(book_model).filter(book_model.id == book_id).first()
    if not book:
        logger.warning(f"Book not found with ID: {book_id}")
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    
    elapsed = time.time() - start_time
    logger.info(f"Book {book_id} retrieved from database in {elapsed:.4f}s")
    
    book_dict = za_response.model_validate(book, from_attributes=True).model_dump()
    book_string = json.dumps(book_dict)
    r.set(cache_key, book_string, ex=60)
    return book

def create_book(request_body: book_create, db: Session):
    logger.debug(f"Creating book: {request_body.book_name}")
    
    reqbody_dict = request_body.model_dump()
    book_author = db.query(Author).filter(Author.name == reqbody_dict["author_name"]).first()
    if not book_author:
        logger.warning(f"Author not found for book: {request_body.book_name}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="there's no author with this name bro")

    reqbody_dict["author_id"] = book_author.id
    db_book = book_model(**reqbody_dict)
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    
    logger.info(f"Book created: {db_book.book_name} by {book_author.name}")
    return db_book

def update_book(db: Session, request_body: book_update, book_id: int):
    start_time = time.time()
    logger.debug(f"Updating book ID: {book_id}")
    
    book_to_update = db.query(book_model).filter(book_model.id == book_id).first()
    if book_to_update is None:
        logger.warning(f"Book not found for update: {book_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="there's no book with this id bro")
    
    reqbody_dict = request_body.model_dump(exclude_unset=True)
    for field, value in reqbody_dict.items():
        setattr(book_to_update, field, value)
    db.commit()
    db.refresh(book_to_update)

    r.delete(f'book:{book_id}')
    
    elapsed = time.time() - start_time
    logger.info(f"Book {book_id} updated in {elapsed:.4f}s")
    return book_to_update

def delete_book(db: Session, book_id: int):
    logger.debug(f"Deleting book ID: {book_id}")
    
    book_to_delete = db.query(book_model).filter(book_model.id == book_id).first()
    if book_to_delete is None:
        logger.warning(f"Book not found for deletion: {book_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="there's no book with this id bro")
    
    db.delete(book_to_delete)
    db.commit()
    r.delete(f'book:{book_id}')
    
    logger.info(f"Book {book_id} deleted successfully")

# ========== AUTHOR CRUD FUNCTIONS ==========
def get_all_authors(skip, limit, db: Session):
    logger.debug(f"Getting all authors with skip={skip}, limit={limit}")
    authors = db.query(Author).order_by(Author.id).offset(skip).limit(limit).all()
    logger.debug(f"Returning {len(authors)} authors")
    return authors

def get_author_by_id(db: Session, author_id: int):
    logger.debug(f"Getting author with ID: {author_id}")
    author = db.query(Author).filter(Author.id == author_id).first()
    if author is None:
        logger.warning(f"Author not found with ID: {author_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="there's no author with this id bro")
    return author

def create_author(db: Session, request_body: Author_create):
    logger.debug(f"Creating author: {request_body.email}")
    
    reqbody_dict = request_body.model_dump()
    reqbody_dict["hashed_password"] = auth.hash_psw(reqbody_dict.pop("password"))
    db_author = Author(**reqbody_dict)
    db.add(db_author)
    db.commit()
    db.refresh(db_author)
    
    logger.info(f"Author created: {db_author.email}")
    return db_author

def update_author(db: Session, request_body: Author_update, author_id: int):
    start_time = time.time()
    logger.debug(f"Updating author ID: {author_id}")
    
    author_to_update = db.query(Author).filter(Author.id == author_id).first()
    if author_to_update is None:
        logger.warning(f"Author not found for update: {author_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="there's no author with this id bro")
    
    reqbody_dict = request_body.model_dump(exclude_unset=True)
    if "password" in reqbody_dict:
        reqbody_dict["hashed_password"] = auth.hash_psw(reqbody_dict.pop("password"))
    
    for field, value in reqbody_dict.items():
        setattr(author_to_update, field, value)
    db.commit()
    db.refresh(author_to_update)
    
    elapsed = time.time() - start_time
    logger.info(f"Author {author_id} updated in {elapsed:.4f}s")
    return author_to_update

def delete_author(db: Session, author_id: int):
    logger.debug(f"Deleting author ID: {author_id}")
    
    author_to_delete = db.query(Author).filter(Author.id == author_id).first()
    if author_to_delete is None:
        logger.warning(f"Author not found for deletion: {author_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="there's no author with this id bro")
    
    db.delete(author_to_delete)
    db.commit()
    
    logger.info(f"Author {author_id} deleted successfully")

# ========== HELPER FUNCTIONS ==========
def check_author_exists(request_body: Author_create, db: Session) -> bool:
    email = request_body.email
    exists = db.query(Author).filter(Author.email == email).first() is not None
    if exists:
        logger.debug(f"Author already exists: {email}")
    return exists

# ========== WEBSOCKET FUNCTIONS ==========
async def broadcast(book_name: str):
    logger.debug(f"Broadcasting new book: {book_name}")
    for connection in main.connections:
        try:
            await connection.send_text(f'New book added :{book_name}')
        except Exception as e:
            logger.error(f"Failed to broadcast to connection: {e}", exc_info=True)
    logger.debug(f"Broadcast complete for: {book_name}")

# ========== CACHE FUNCTIONS ==========
def clear_all_cache():
    """Clear all Redis cache (for testing)"""
    logger.info("Clearing all Redis cache")
    r.flushdb()
    logger.info("Redis cache cleared")
    return {"message": "Cache cleared"}