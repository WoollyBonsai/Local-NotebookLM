from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import datetime
import os

DATABASE_URL = "sqlite:///./eduguard.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Notebook(Base):
    __tablename__ = "notebooks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    documents = relationship("Document", back_populates="notebook", cascade="all, delete-orphan")
    history = relationship("ChatHistory", back_populates="notebook", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    notebook_id = Column(Integer, ForeignKey("notebooks.id"))
    notebook = relationship("Notebook", back_populates="documents")
    concepts = relationship("Concept", back_populates="document", cascade="all, delete-orphan")

class Concept(Base):
    __tablename__ = "concepts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    definition = Column(Text)
    page_number = Column(Integer)
    document_id = Column(Integer, ForeignKey("documents.id"))
    document = relationship("Document", back_populates="concepts")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    notebook_id = Column(Integer, ForeignKey("notebooks.id"))
    role = Column(String) # "user" or "bot"
    text = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    notebook = relationship("Notebook", back_populates="history")

class DiaryEntry(Base):
    __tablename__ = "diary_entries"
    id = Column(Integer, primary_key=True, index=True)
    raw_text = Column(Text)
    synthesized_text = Column(Text) # LLM summary/insights
    response_text = Column(Text) # The companion's reply
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)
