from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL=os.getenv('DATABASE_URL')# i hate you 

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URL,echo=True)
#connection = engine.connect()
session_factory=sessionmaker(autocommit=False,autoflush=False,bind=engine)#session factory

def get_db(): # dependency function 
    db=session_factory()
    try:
        yield db
    finally:
        db.close()



# Run this once, usually in a separate script or at startup
#Base.metadata.create_all(bind=engine)

    

 



