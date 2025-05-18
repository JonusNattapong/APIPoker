from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    credits: float
    class Config:
        orm_mode = True

class TableCreate(BaseModel):
    name: str

class TableOut(BaseModel):
    id: int
    name: str
    owner_id: int
    class Config:
        orm_mode = True

class GameCreate(BaseModel):
    table_id: int

class GameOut(BaseModel):
    id: int
    table_id: int
    owner_id: int
    state: str
    class Config:
        orm_mode = True
