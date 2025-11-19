import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Book, Chapter, Comment, LibraryItem

app = FastAPI(title="Novel Sharing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helpers
class ObjectIdStr(BaseModel):
    id: str


def to_obj_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")


@app.get("/")
def root():
    return {"message": "Novel Sharing Backend running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# Books
@app.post("/api/books", response_model=ObjectIdStr)
def create_book(book: Book):
    book_id = create_document("book", book)
    return {"id": book_id}


@app.get("/api/books")
def list_books(
    q: Optional[str] = None,
    tag: Optional[str] = None,
    category: Optional[str] = None,
    genre: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100)
):
    filter_dict = {}
    if q:
        filter_dict["title"] = {"$regex": q, "$options": "i"}
    if tag:
        filter_dict["tags"] = tag
    if category:
        filter_dict["categories"] = category
    if genre:
        filter_dict["genre"] = genre

    books = get_documents("book", filter_dict, limit)
    for b in books:
        b["_id"] = str(b["_id"])
    return books


@app.get("/api/books/{book_id}")
def get_book(book_id: str):
    doc = db["book"].find_one({"_id": to_obj_id(book_id)})
    if not doc:
        raise HTTPException(404, "Book not found")
    doc["_id"] = str(doc["_id"])
    return doc


# Chapters
@app.post("/api/chapters", response_model=ObjectIdStr)
def create_chapter(chapter: Chapter):
    # If chapter_number not provided, auto-increment based on existing chapters
    if chapter.chapter_number is None:
        count = db["chapter"].count_documents({"book_id": chapter.book_id})
        chapter.chapter_number = count + 1
    chapter_id = create_document("chapter", chapter)
    return {"id": chapter_id}


@app.get("/api/books/{book_id}/chapters")
def list_chapters(book_id: str):
    chapters = list(db["chapter"].find({"book_id": book_id}).sort("chapter_number", 1))
    for c in chapters:
        c["_id"] = str(c["_id"])
    return chapters


@app.get("/api/chapters/{chapter_id}")
def get_chapter(chapter_id: str):
    doc = db["chapter"].find_one({"_id": to_obj_id(chapter_id)})
    if not doc:
        raise HTTPException(404, "Chapter not found")
    doc["_id"] = str(doc["_id"])
    return doc


# Comments
@app.post("/api/comments", response_model=ObjectIdStr)
def add_comment(comment: Comment):
    comment_id = create_document("comment", comment)
    return {"id": comment_id}


@app.get("/api/books/{book_id}/comments")
def list_comments(book_id: str):
    comments = list(db["comment"].find({"book_id": book_id}).sort("created_at", -1))
    for c in comments:
        c["_id"] = str(c["_id"])
    return comments


# Library (user shelves)
@app.post("/api/library", response_model=ObjectIdStr)
def add_to_library(item: LibraryItem):
    existing = db["libraryitem"].find_one({"user_id": item.user_id, "book_id": item.book_id})
    if existing:
        return {"id": str(existing["_id"])}
    new_id = create_document("libraryitem", item)
    return {"id": new_id}


@app.get("/api/library/{user_id}")
def get_library(user_id: str):
    items = list(db["libraryitem"].find({"user_id": user_id}))
    book_ids = [it["book_id"] for it in items]
    books = list(db["book"].find({"_id": {"$in": [ObjectId(b) for b in book_ids if ObjectId.is_valid(b)]}}))
    book_map = {str(b["_id"]): b for b in books}
    for b in books:
        b["_id"] = str(b["_id"])
    # return books in the order of library items
    result = [book_map.get(bid) for bid in book_ids if book_map.get(bid)]
    return result


# Discover endpoints
@app.get("/api/discover/trending")
def discover_trending(limit: int = 12):
    # naive trending: sort by number of chapters desc, then recent updated
    pipeline = [
        {"$lookup": {"from": "chapter", "localField": "_id", "foreignField": "book_id", "as": "chapters"}},
        {"$addFields": {"chapters_count": {"$size": {
            "$filter": {
                "input": "$chapters",
                "as": "c",
                "cond": {"$ne": ["$$c", None]}
            }
        }}}},
        {"$sort": {"chapters_count": -1, "updated_at": -1}},
        {"$limit": limit}
    ]
    data = list(db["book"].aggregate(pipeline))
    for d in data:
        d["_id"] = str(d["_id"])
    return data


@app.get("/api/discover/tags")
def discover_by_tag(tag: str, limit: int = 24):
    books = get_documents("book", {"tags": tag}, limit)
    for b in books:
        b["_id"] = str(b["_id"])
    return books


@app.get("/api/discover/category")
def discover_by_category(category: str, limit: int = 24):
    books = get_documents("book", {"categories": category}, limit)
    for b in books:
        b["_id"] = str(b["_id"])
    return books


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
