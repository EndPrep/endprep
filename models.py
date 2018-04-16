from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine, UniqueConstraint
import datetime


Base = declarative_base()


# User Table
class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False)
    picture = Column(String(300))
    rating = Column(Integer,default=0)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
            'email': self.email
        }


# category table
class Subject(Base):
    __tablename__ = 'subject'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), unique=True)
    picture = Column(String(300))
    # Add a property decorator to serialize information from this database

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id,
        }


class Chapter(Base):
    __tablename__ = 'chapter'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    about = Column(String(500), nullable=False)
    subject_name = Column(String, ForeignKey('subject.name'))
    subject = relationship(Subject)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'title': self.title,
            'about': self.about,
            'subject_name': self.subject_name,
        }


class File(Base):
    __tablename__ = 'file'

    name = Column(String(200), nullable=False)
    file_name = Column(String(200), nullable=False)
    id = Column(Integer, primary_key=True)
    rating = Column(Integer,default=0)
    time = Column(String)
    user_id = Column(Integer, ForeignKey('user.id'))
    chapter_id = Column(Integer, ForeignKey('chapter.id'))
    subject_id = Column(Integer, ForeignKey('subject.id'))
    user = relationship(User)
    chapter = relationship(Chapter)
    subject = relationship(Subject)
    # Returning Columns in Json format

    @property
    def serialize(self):
        return {
            'name': self.name,
            'file_name': self.file_name,
            'id': self.id,
            'rating': self.rating,
            'updated_time': self.time,
        }


class Comment(Base):
    __tablename__ = 'comment'

    data = Column(String(500), nullable=False)
    id = Column(Integer, primary_key=True)
    time = str(datetime.datetime.now())
    file_id = Column(Integer, ForeignKey('file.id'))
    user_id = Column(Integer, ForeignKey('user.id'))
    file = relationship(File)
    user = relationship(User)


class Topic(Base):
    __tablename__ = 'topic'

    title = Column(String(200), nullable=False)
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('file.id'))
    file = relationship(File)


engine = create_engine(
                        'postgresql://octauser:dynamic*_*website@localhost/octa')  # noqa

Base.metadata.create_all(engine)
