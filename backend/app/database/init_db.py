from app.database.connection import Base, engine
from app.database import models

def initialize_database():
    Base.metadata.create_all(bind=engine)
    print("DataTrace database tables are ready.")
    

if __name__ == "__main__":
    initialize_database()
    