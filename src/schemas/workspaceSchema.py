from pydantic import BaseModel


class WorkSpaceSchema(BaseModel):
    _id: int  # id is private.
    user_id: int
    name: str

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True
