from sqlalchemy import text
from app.db.database import engine
with engine.connect() as con:
    rs = con.execute(text("PRAGMA table_info(extraction_requests);"))
    for row in rs:
        print(row)
