from fastapi import FastAPI,Depends,HTTPException,status,Request,BackgroundTasks,WebSocket,WebSocketDisconnect
#CORS
from fastapi.middleware.cors import CORSMiddleware
#rate limiter
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
#websocket
from typing import List #list[websockets]
#my files
from schemas import book_create,za_response,book_update,Author_create,Author_update,Author_response,my_log_in,token_response,Role
from db_connection import get_db,engine
from sqlalchemy.orm import Session
import my_funcs
from db_models import base,book_model,Author
from datetime import timedelta,datetime,timezone
import auth


app=FastAPI()



# Create the rate limiter (tracks requests by IP address)
limiter = Limiter(key_func=get_remote_address)

# Store it in the app
app.state.limiter = limiter

# Tell FastAPI what to do when rate limit is exceeded
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#base.metadata.drop_all(bind=engine)
base.metadata.create_all(bind=engine)


@app.get("/books",response_model=list[za_response])#makes the response a list of za_response objects
@limiter.limit("60/minute")
def get_all_books(request:Request,skip:int=0,limit:int=2,db:Session=Depends(get_db)):
    return my_funcs.get_all_books(skip,limit,db)


@app.get("/book/{book_id}",response_model=za_response)
@limiter.limit("60/minute")
def get_book_by_id(request:Request,book_id:int,db:Session=Depends(get_db)):
    return my_funcs.get_book(db,book_id)

@app.post("/create-book",response_model=za_response,status_code=201)
@limiter.limit("10/minute")
async def create_book(request:Request,request_body:book_create,db:Session=Depends(get_db)):
    new_book=my_funcs.create_book(request_body,db)
    await my_funcs.broadcast(new_book.book_name)
    return new_book

@app.put("/update-book/{book_id}",response_model=za_response)
@limiter.limit("10/minute")
def update_book(request:Request,book_id:int,request_body:book_update,db:Session=Depends(get_db)):
    return my_funcs.update_book(db,request_body,book_id)

@app.delete("/delete-book/{book_id}",status_code=204)
@limiter.limit("5/minute")
def delete_book(request:Request,book_id:int,db:Session=Depends(get_db)):
    return my_funcs.delete_book(db,book_id)

#author crud functions

@app.get("/authors",response_model=list[Author_response])#makes the response a list of Author_response objects
@limiter.limit("60/minute")
def get_all_authors(request:Request,skip:int=0,limit:int=2,db:Session=Depends(get_db)):
    return my_funcs.get_all_authors(skip,limit,db)

@app.get("/author/{author_id}",response_model=Author_response)
@limiter.limit("60/minute")
def get_author_by_id(request:Request,author_id:int,db:Session=Depends(get_db)):
   return my_funcs.get_author_by_id(db,author_id)

@app.post("/create-author",response_model=Author_response,status_code=201)
@limiter.limit("10/minute")
def create_author(request:Request,request_body:Author_create,db:Session=Depends(get_db)):
    if my_funcs.check_author_exists(request_body,db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="author already exists bro ")
    return my_funcs.create_author(db,request_body)
    
@app.post("/create-author-no-return",status_code=201)
@limiter.limit("10/minute")
def create_author_no_return(
    background_tasks:BackgroundTasks,
    request:Request,
    request_body:Author_create,
    db:Session=Depends(get_db)
    ):
    if my_funcs.check_author_exists(request_body,db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="author already exists bro ")
    background_tasks.add_task(my_funcs.create_author,db,request_body)
    return "welcome author , you're now an author and i will not return anything sorry "


@app.put("/update-author/{author_id}",response_model=Author_response)
@limiter.limit("10/minute")
def update_author(request:Request,author_id:int,request_body:Author_update,db:Session=Depends(get_db)):
    return my_funcs.update_author(db,request_body,author_id)
    

@app.delete("/delete-author/{author_id}",status_code=204)
@limiter.limit("5/minute")
def delete_author(request:Request,author_id:int,db:Session=Depends(get_db)):
    return my_funcs.delete_author(db,author_id)
    
# relationship endpoints

@app.get("/author-books/{author_id}",response_model=list[za_response])
@limiter.limit("60/minute")
def get_author_books(request:Request,author_id:int,db:Session=Depends(get_db)):
    author = my_funcs.get_author_by_id(db,author_id)
    return author.books

@app.get("/book-author/{book_id}",response_model=Author_response)
@limiter.limit("60/minute")
def get_book_author(request:Request,book_id:int,db:Session=Depends(get_db)):
    book = my_funcs.get_book(db,book_id)
    return book.author

#endpoints requiring security
@app.post("/login")
@limiter.limit("5/minute")
def log_in(request:Request,log_in_data:my_log_in,db:Session=Depends(get_db))->token_response:
    author=auth.authenticate_author(log_in_data.email,log_in_data.password,db)
    if not author:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="wrong email or password",
            headers={"WWW-Authenticate": "Bearer"}
            )
    expiry_time=datetime.now(timezone.utc)+timedelta(minutes=30)
    data={
        "author_id":author.id
        
    }
    token=auth.create_access_token(data,expiry_time)
    return {"access_token": token, "token_type": "bearer"}

#protected endpoint
@app.get("/my-profile",response_model=Author_response)
@limiter.limit("60/minute")
def get_profile(request:Request,author: Author = Depends(auth.get_current_author),db:Session=Depends(get_db)):
    return author

#get author books protected version
@app.get("/my-books",response_model=list[za_response])
@limiter.limit("60/minute")
def get_my_books(request:Request,author: Author = Depends(auth.get_current_author),db:Session=Depends(get_db)):
    return author.books

#authorized function 
@app.delete('/delete-other-author/{author_id}',status_code=204)
@limiter.limit("3/minute")
def delete_other_author(request:Request,author_id:int,_=Depends(auth.require_admin),db:Session=Depends(get_db)):
        return my_funcs.delete_author(db,author_id)

#websocket

connections:List[WebSocket]=[]
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Step 1: Accept the connection (REQUIRED)
    await websocket.accept()
    
    # Step 2: Wait for messages forever (or until disconnect)
    connections.append(websocket)
    try:
        while True:
        # Step 3: Receive a message from client
            data = await websocket.receive_text()
        
        # Step 4: Send a message back to client
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        print("websocket disconnected")