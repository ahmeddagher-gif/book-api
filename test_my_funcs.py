# test_my_funcs.py - Copy of my_funcs.py but with Redis disabled

from db_models import book_model, Author
from schemas import Author_create, Author_update, book_create, book_update
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import auth

# NO REDIS HERE

def get_book(db: Session, book_id):
    # Direct database query - no Redis cache
    book = db.query(book_model).filter(book_model.id == book_id).first()
    if not book:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return book

def update_book(db: Session, request_body: book_update, book_id: int):
    book_to_update = db.query(book_model).filter(book_model.id == book_id).first()
    if book_to_update is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    reqbody_dict = request_body.model_dump(exclude_unset=True)
    for field, value in reqbody_dict.items():
        setattr(book_to_update, field, value)
    db.commit()
    db.refresh(book_to_update)
    # NO REDIS DELETE
    return book_to_update

def delete_book(db: Session, book_id: int):
    book_to_delete = db.query(book_model).filter(book_model.id == book_id).first()
    if book_to_delete is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    db.delete(book_to_delete)
    db.commit()
    # NO REDIS DELETE