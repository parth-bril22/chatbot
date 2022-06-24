from fastapi import APIRouter
from src.endpoints import users, node, flow, chat_publish, workspace
router = APIRouter()
router.include_router(users.router)
router.include_router(node.router)
router.include_router(flow.router)
# router.include_router(chat_publish.router)
router.include_router(workspace.router)
