from fastapi import APIRouter
from src.endpoints import users, node
router = APIRouter()
router.include_router(users.router)
router.include_router(node.router)