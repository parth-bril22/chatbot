# build a schema using pydantic
from pydantic import BaseModel

class User(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    # register_time: datetime
    

    class Config:
        orm_mode = True


# class FullUser(BaseModel):
#     id: int
#     email: str
#     password: str
#     first_name: str
#     last_name: str
#     register_time: datetime
    

#     class Config:
#         orm_mode = True


class LoginSchema(BaseModel):
    email : str
    password : str

    class Config:
        orm_mode = True
    
class PasswordResetSchema(BaseModel):
    password: str
    confirm_password : str

    class Config:
        orm_mode = True

class PasswordChangeSchema(BaseModel):
    current_password: str
    new_password: str
    confirm_password : str

    class Config:
        orm_mode = True

class EmailSchema(BaseModel):
    email:str

    class Config:
        orm_mode = True

