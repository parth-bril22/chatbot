from typing import Dict
from pydantic import BaseModel

class SlackSchema(BaseModel):
    data: Dict
    userId: int

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True