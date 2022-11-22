from pydantic import BaseModel


class User(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str

    class Config:
        orm_mode = True


class LoginSchema(BaseModel):
    email: str
    password: str

    class Config:
        orm_mode = True


class PasswordResetSchema(BaseModel):
    password: str
    confirm_password: str

    class Config:
        orm_mode = True


class ChangePasswordSchema(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    class Config:
        orm_mode = True


class EmailSchema(BaseModel):
    email: str

    class Config:
        orm_mode = True
