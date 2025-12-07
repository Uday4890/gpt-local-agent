from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..schemas.post import Post, PostCreate
from ..models.post import Post as PostModel
from ..database import get_db

router = APIRouter()

@router.post("/", response_model=Post)
def create_post(post: PostCreate, db: Session = Depends(get_db)):
    db_post = db.query(PostModel).filter(PostModel.title == post.title).first()
    if db_post:
        raise HTTPException(status_code=400, detail="Post already exists")
    new_post = PostModel(title=post.title, content=post.content)
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post

@router.get("/", response_model=List[Post])
def read_posts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    posts = db.query(PostModel).offset(skip).limit(limit).all()
    return posts

@router.get("/{post_id}", response_model=Post)
def read_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(PostModel).filter(PostModel.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post
