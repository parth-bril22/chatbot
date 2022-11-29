from pydantic import BaseModel


class CreateVariable(BaseModel):
    name: str
    type: str
    userId: int
    value: str

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True
