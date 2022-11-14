from pydantic import BaseModel


class WorkSpaceSchema(BaseModel):
    _id: int  # id is made private by the "_" before its name, so frontend need not enter it.
    user_id: int
    name: str

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True
