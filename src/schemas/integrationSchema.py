from typing import Dict
from pydantic import BaseModel

class SlackSchema(BaseModel):
    data: Dict
    userId: int

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True


class EmailSchema(BaseModel):
    from_email: str
    secret:str
    to_email: str
    subject:str
    message:str
    customEmail:bool


    class Config:
        orm_mode = True
        underscore_attrs_are_private = True