import os
import sys
from sqlalchemy.orm import Session

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hub.db.session import SessionLocal
from hub.db import schema

def check_kb():
    db = SessionLocal()
    articles = db.query(schema.KBArticle).all()
    print(f"Total articles in KB: {len(articles)}")
    for art in articles:
        print(f"ID: {art.id} | Title: {art.title} | Category: {art.category} | Status: {art.status}")
    
    meta = db.query(schema.KBMeta).first()
    if meta:
        print(f"KB Version: {meta.kb_version} | Updated At: {meta.updated_at}")
    else:
        print("KB Meta not found.")
    
    db.close()

if __name__ == "__main__":
    check_kb()
