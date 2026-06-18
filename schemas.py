from pydantic import BaseModel,Field
from enum import Enum

class book_create(BaseModel):
    book_name:str=Field(min_length=3)
    author_name:str
    pages:int

class za_response(BaseModel):
    id:int
    book_name:str
    author_name:str
    pages:int

class book_update(BaseModel):
     book_name:str=Field(default=None,min_length=3)
     pages:int=Field(default=None)

    #it's basically book_create but with the default set to none it doesn't even matter because i'll make exclude_unset=true so it exxcludes anything unset so it's like the default isn't even there then why did you make it in the first place so fastapi doesn't give me an error when validating against the schema when seeing there's a missed param or value i didn't fill so when it's none it doesn't give me an error 


#author schemas

class Author_create(BaseModel):
    name:str
    email: str = Field(pattern=r"^\S+@\S+\.\S+$")
    password:str #plain password


class Author_update(BaseModel):
    name:str=Field(default=None)
    email: str = Field(default=None,pattern=r"^\S+@\S+\.\S+$")
    password:str=Field(default=None) #plain password

class Author_response(BaseModel):
    id:int
    name:str
    email:str

class Role(Enum):
    ADMIN='admin'
    AUTHOR='author'


class my_log_in(BaseModel):
    email:str
    password:str
    role:Role

class token_response(BaseModel):  #this is what i will return to the postman or client after the log in
    access_token:str
    token_type:str







