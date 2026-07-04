from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import os

DB_PATH = "eduguard.db"
engine = create_engine(f"sqlite:///{DB_PATH}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    concepts = relationship("Concept", back_populates="document")

class Concept(Base):
    __tablename__ = "concepts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    definition = Column(Text)
    page_number = Column(Integer)
    document_id = Column(Integer, ForeignKey("documents.id"))
    
    document = relationship("Document", back_populates="concepts")

# Create tables
Base.metadata.create_all(bind=engine)
