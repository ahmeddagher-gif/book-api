import main
import redis
import json
from db_models import book_model,Author
from schemas import Author_create,Author_update, book_create,book_update,my_log_in,za_response
from sqlalchemy.orm import Session
from fastapi import HTTPException,status
import auth
#env 
import os
from dotenv import load_dotenv

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)




def get_all_books(skip,limit,db:Session):
    books=db.query(book_model).order_by(book_model.id).offset(skip).limit(limit).all()
     ## skip the first `skip` rows, then return `limit` rows
    return books

def get_book(db:Session,book_id):
    cache_key=f'book:{book_id}'
    cached_book=r.get(cache_key)

    if cached_book:  #cache hit
        return json.loads(cached_book) # turned the cached book from string to dict
    book=db.query(book_model).filter(book_model.id==book_id).first()
    if not book:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    book_dict=za_response.model_validate(book,from_attributes=True).model_dump()# you turned the sqlalchemy model to pydantic model then turned the pydantic model into a dict
    book_string=json.dumps(book_dict)
    r.set(cache_key,book_string,ex=60)
    return book




def create_book(request_body:book_create,db:Session):
    reqbody_dict=request_body.model_dump()
    book_author=db.query(Author).filter(Author.name==reqbody_dict["author_name"]).first()
    if not book_author:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="there's no author with this name bro")

    reqbody_dict["author_id"]=book_author.id

    db_book=book_model(**reqbody_dict)
    db.add(db_book)
    db.commit()
    db.refresh(db_book)   
    return db_book
 
def update_book(db:Session,request_body:book_update,book_id:int):
    book_to_update=db.query(book_model).filter(book_model.id==book_id).first()
    if book_to_update is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="there's no book with this id bro")
    reqbody_dict=request_body.model_dump(exclude_unset=True)# what excludes unset does is that it excludes any value i didn't set ,so the default None value doesn't get included in the reqbody_dict and it doesn't get updated to None in the database 
    for field,value in reqbody_dict.items():
        setattr(book_to_update,field,value)
    db.commit()
    db.refresh(book_to_update)

    r.delete(f'book:{book_id}')
    return book_to_update


def delete_book(db:Session,book_id:int):
    book_to_delete=db.query(book_model).filter(book_model.id==book_id).first()
    if book_to_delete is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="there's no book with this id bro")
    db.delete(book_to_delete)
    db.commit()
    r.delete(f'book:{book_id}')

#author crud functions

def get_all_authors(skip,limit,db:Session):
    authors=db.query(Author).order_by(Author.id).offset(skip).limit(limit).all()
     ## skip the first `skip` rows, then return `limit` rows
    return authors

def get_author_by_id(db:Session,author_id:int):
    author=db.query(Author).filter(Author.id==author_id).first()
    if author is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="there's no author with this id bro")
    return author

def create_author(db:Session,request_body:Author_create):
    reqbody_dict=request_body.model_dump()
    reqbody_dict["hashed_password"]=auth.hash_psw(reqbody_dict.pop("password"))
    db_author=Author(**reqbody_dict)
    db.add(db_author)
    db.commit()
    db.refresh(db_author)   
    return db_author

def update_author(db:Session,request_body:Author_update,author_id:int):
    author_to_update=db.query(Author).filter(Author.id==author_id).first()
    if author_to_update is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="there's no author with this id bro")
    reqbody_dict=request_body.model_dump(exclude_unset=True)# what excludes unset does is that it excludes any value i didn't set so the default None value doesn't get included in the reqbody_dict and it doesn't get updated to None in the database normally if the client sends for example {"name":"new name"} in the request body then the reqbody_dict would be {"name":"new name","email":None,"password":None} but with exclude_unset=True the reqbody_dict would be just {"name":"new name"} so only the name gets updated and the email and password stay the same but if i didn't use exclude_unset then the email and password would get updated to None which is not what i want
    if "password" in reqbody_dict:
        reqbody_dict["hashed_password"]=auth.hash_psw(reqbody_dict.pop("password"))
    for field,value in reqbody_dict.items():
        setattr(author_to_update,field,value)
    db.commit()
    db.refresh(author_to_update)
    return author_to_update

def delete_author(db:Session,author_id:int):
    author_to_delete=db.query(Author).filter(Author.id==author_id).first()
    if author_to_delete is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="there's no author with this id bro")
    db.delete(author_to_delete)
    db.commit()

#signup - log in functions
def check_author_exists(request_body:Author_create,db:Session)->bool:
    email=request_body.email
    if db.query(Author).filter(Author.email==email).first():
        return True
    return False

    

#websocket functions 

async def broadcast(book_name:str):
    for connection in main.connections:
        await connection.send_text(f'New book added :{book_name}')

# my_funcs.py
def clear_all_cache():
    """Clear all Redis cache (for testing)"""
    r.flushdb()
    return {"message": "Cache cleared"}    




