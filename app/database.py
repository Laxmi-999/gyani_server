from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
from app.config import settings

engine = create_engine(settings.database_url)
#establish database connection pooling and driver configuration

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# 1. Setting up the "Factory" (eg: The Espresso Machine)
#You haven't made any coffee yet (no database connections are open).
#You are just configuring the machine's default settings: water pressure, bean grind size, and water tank source (bind=engine).
#Now, whenever a customer orders a coffee, you don't build a new espresso machine from scratch. You just press the button on the machine you already set up:
# ❌ WITHOUT A FACTORY (Tedious & Easy to mess up):
# Every route needs to remember all these exact configuration settings manually!
# ✅ WITH A FACTORY (Clean & Centralized):
# You set the rules once at application startup.

# Later in your code, creating a session is just 1 simple line:
# eg: db = SessionLocal()






Base = declarative_base()
#This line creates a base class that acts as a bridge between Python and SQL tables.

def get_db():
    db= SessionLocal()
    try:
        yield db
        #It creates the database session (db).
        #It hand-offs db to your API endpoint so your code can run queries (e.g., fetching a user or inserting a post).
        #It freezes get_db() right on that line while your API endpoint finishes its job.
    finally:
        db.close()



