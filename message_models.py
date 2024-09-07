from sqlalchemy.engine.base import Engine
from sqlmodel import SQLModel, Field, create_engine

class Message(SQLModel, table=True):
    __tablename__ = "messages"
    id: int = Field(primary_key=True)
    date: str
    date_unixtime: int = Field(index=True)
    year: int = Field(index=True)
    month: int = Field(index=True)
    day: int = Field(index=True)
    type: str
    from_name: str = Field(index=True)
    from_id: str = Field(index=True)
    text: str
    reply_to_message_id: int | None = None
    photo: str | None = None
    file: str | None = None
    oversize_file: bool = False
    thumbnail: str | None = None
    media_type: str | None = None
    mime_type: str | None = None
    duration_seconds: int | None = None
    width: int | None = None
    height: int | None = None
    anon_from_id: str | None = None


class Link(SQLModel, table=True):
    __tablename__ = "links"
    id: int = Field(primary_key=True)
    message_id: int = Field(foreign_key="messages.id")
    link: str
    resolved_link: str | None = None


def activate_db(db_path: str)  -> Engine:
    engine = create_engine(f"sqlite:///{db_path}")
    return engine
