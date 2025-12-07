from sqlalchemy import Column, Integer, String, Text
from ..database import Base

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), unique=True, index=True, nullable=False)
    content = Column(Text, nullable=False)
