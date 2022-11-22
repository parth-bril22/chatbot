from pydantic import BaseModel
from typing import List


class AddMember(BaseModel):
    _id: int  # id is private.
    user_id: int
    name: str
    isavailable: bool = False

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True


class MemberSchema(BaseModel):
    _id: int  # id is private.
    user_id: List[int]

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True
