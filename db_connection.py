from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker

DATABASE_URL='postgresql://neondb_owner:npg_gXzkn76DyNUR@ep-purple-lab-aeo90qof-pooler.c-2.us-east-2.aws.neon.tech/book_project?sslmode=require&channel_binding=require'



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

    

 



