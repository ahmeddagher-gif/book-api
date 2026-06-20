from sqlalchemy.orm import declarative_base 
from schemas import Role
from sqlalchemy import Column, Integer, String, ForeignKey,Enum
from sqlalchemy.orm import relationship
from typing import Optional
base = declarative_base()



class book_model(base):
    __tablename__="books"
    id=Column(Integer,primary_key=True)
    book_name=Column(String)
    author_name=Column(String)
    pages = Column(Integer, nullable=False)
    author_id = Column(Integer, ForeignKey("authors.id",ondelete="CASCADE"), nullable=True)
    author = relationship("Author", back_populates="books")  # this is saying give me the author that has the same id as this book's user_id so it's like db.query(Author).filter(Author.id == book_model.user_id).first() but here it's not a list it's just one author because a book can only belong to one author

class Author(base):
    __tablename__="authors"
    name=Column(String)
    email=Column(String,unique=True,nullable=False,index=True)
    hashed_password=Column(String,unique=True,nullable=False)
    id=Column(Integer,primary_key=True,nullable=False)
    books=relationship("book_model", back_populates="author",cascade="all, delete-orphan")  # what relationship does is fire a query to the database and it says give me all the books that have the same user_id as this user's id(which is the foreign key condition) it fires this query when i access books(User.books) so you could imagine that books=db.query(book_model).filter(book_model.user_id==User.id).all() so it's like a list of books that belong to this user but why can't we just write this query ourselves? well we can but it's just more convenient to use relationships it allows us to do alot more things and you can kinda give this query properties









