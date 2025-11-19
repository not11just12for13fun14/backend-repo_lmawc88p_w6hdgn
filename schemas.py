"""
Database Schemas for Novel Platform

Each Pydantic model corresponds to a MongoDB collection (lowercased class name).
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class User(BaseModel):
    username: str = Field(..., description="Display name")
    email: Optional[str] = Field(None, description="Email for contact")
    avatar_url: Optional[str] = Field(None, description="Profile image URL")


class Book(BaseModel):
    title: str = Field(..., description="Book title")
    description: Optional[str] = Field(None, description="Short synopsis")
    author_name: str = Field(..., description="Author's display name")
    cover_url: Optional[str] = Field(None, description="Cover image URL")
    tags: List[str] = Field(default_factory=list, description="Freeform tags")
    categories: List[str] = Field(default_factory=list, description="High-level categories")
    genre: Optional[str] = Field(None, description="Primary genre")
    status: str = Field("ongoing", description="ongoing | completed | hiatus")


class Chapter(BaseModel):
    book_id: str = Field(..., description="Parent book id")
    title: str = Field(..., description="Chapter title")
    content: str = Field(..., description="Markdown or text content")
    chapter_number: Optional[int] = Field(None, description="Sequential number")


class Comment(BaseModel):
    book_id: str = Field(..., description="Target book id")
    user_name: str = Field(..., description="Commenter's name")
    content: str = Field(..., description="Comment text")


class LibraryItem(BaseModel):
    user_id: str = Field(..., description="Identifier for user (no auth in demo)")
    book_id: str = Field(..., description="Book id")
