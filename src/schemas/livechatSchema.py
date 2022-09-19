from pydantic import BaseModel
from typing import  List
class AgentSchema(BaseModel):
    _id: int #id is made private by the "_" before its name, so frontend need not enter it.
    user_id :int
    name : str
    isavailable : bool = False
    
    class Config:
        orm_mode = True
        underscore_attrs_are_private = True


class MemberSchema(BaseModel):
    _id: int  # id is made private by the "_" before its name, so frontend need not enter it.
    user_id: List[int]

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True