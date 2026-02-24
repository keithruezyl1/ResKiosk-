import json
import argparse
import os
import sys
from datetime import datetime

# Add the project root to sys.path to allow importing hub modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hub.db.session import SessionLocal
from hub.db import schema
from hub.retrieval.embedder import load_embedder, serialize_embedding, get_embeddable_text

def bulk_import(file_path: str):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        try:
            articles_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON format: {e}")
            return

    if not isinstance(articles_data, list):
        print("Error: JSON must be a list of articles.")
        return

    db = SessionLocal()
    embedder = None
    try:
        embedder = load_embedder()
    except Exception as e:
        print(f"Warning: Could not load embedder. Articles will be imported without embeddings. Error: {e}")

    imported_count = 0
    error_count = 0

    print(f"Starting bulk import of {len(articles_data)} items...")

    for data in articles_data:
        try:
            # Validate required fields
            if "title" not in data or "body" not in data:
                print(f"Skipping article missing title or body: {data.get('title', 'Unknown')}")
                error_count += 1
                continue

            article = schema.KBArticle(
                title=data["title"],
                body=data["body"],
                category=data.get("category", "General"),
                status=data.get("status", "published"),
                enabled=data.get("enabled", True)
            )
            article.set_tags(data.get("tags", []))

            # Generate embedding
            if embedder:
                try:
                    text = get_embeddable_text(article)
                    vec = embedder.embed_text(text)
                    article.embedding = serialize_embedding(vec)
                except Exception as e:
                    print(f"Warning: Failed to embed article '{article.title}': {e}")

            db.add(article)
            imported_count += 1
            if imported_count % 5 == 0:
                print(f"Processed {imported_count} articles...")

        except Exception as e:
            print(f"Error importing article '{data.get('title', 'Unknown')}': {e}")
            error_count += 1

    # Update KB Meta version
    try:
        meta = db.query(schema.KBMeta).first()
        if not meta:
            meta = schema.KBMeta(kb_version=1)
            db.add(meta)
        else:
            meta.kb_version += 1
            meta.updated_at = datetime.utcnow()
        db.add(meta)
    except Exception as e:
        print(f"Warning: Could not update KB version info: {e}")

    db.commit()
    db.close()

    print("\nImport Complete!")
    print(f"Successfully imported: {imported_count}")
    print(f"Failed: {error_count}")
    print(f"KB Version incremented.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk import articles into ResKiosk Knowledge Base")
    parser.get_default("file")
    parser.add_argument("--file", type=str, required=True, help="Path to the JSON file containing articles")
    
    args = parser.parse_args()
    bulk_import(args.file)
