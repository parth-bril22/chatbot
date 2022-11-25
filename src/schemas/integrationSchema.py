from typing import Dict
from pydantic import BaseModel


class Slack(BaseModel):
    data: Dict
    userId: int

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True


class SendgridMail(BaseModel):
    from_email: str
    secret: str
    userId: int

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True
