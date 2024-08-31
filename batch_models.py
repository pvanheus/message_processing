from enum import Enum

from sqlalchemy.engine.base import Engine
from sqlmodel import SQLModel, Field

class StateEnum(str, Enum):
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"

class Job(SQLModel, table=True):
    __tablename__ = "jobs"
    id: str = Field(primary_key=True)
    status: StateEnum = Field()
    year: int
    month: int
    start_day: int
    end_day: int
    results_file: str | None = None
    log_message: str | None = None
    start_message_num: int | None = None
    end_message_num: int | None = None
