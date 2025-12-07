from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_session
from app.models.post import Post
from app.schemas.post import PostCreate, PostUpdate, PostInDB

router = APIRouter()

@router.post("/", response_model=PostInDB)
async def create_post(post: PostCreate, session: AsyncSession = Depends(get_session)):
    new_post = Post(**post.dict())
    session.add(new_post)
    await session.commit()
    await session.refresh(new_post)
    return new_post

@router.get("/", response_model=List[PostInDB])
async def read_posts(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Post))
    posts = result.scalars().all()
    return posts

@router.get("/{post_id}", response_model=PostInDB)
async def read_post(post_id: int, session: AsyncSession = Depends(get_session)):
    post = await session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@router.put("/{post_id}", response_model=PostInDB)
async def update_post(post_id: int, post_update: PostUpdate, session: AsyncSession = Depends(get_session)):
    post = await session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    for field, value in post_update.dict(exclude_unset=True).items():
        setattr(post, field, value)
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post

@router.delete("/{post_id}")
async def delete_post(post_id: int, session: AsyncSession = Depends(get_session)):
    post = await session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    await session.delete(post)
    await session.commit()
    return {"ok": True}
