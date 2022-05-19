# build a schema using pydantic
import json
from pydantic import BaseModel
from datetime import datetime

from src.models.node import Diagram


class FlowSchema(BaseModel):
    _id: int
    _created_at: datetime
    _updated_at: datetime
    name : str
    user_id : int

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True