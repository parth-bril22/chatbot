from fastapi import APIRouter
from src.endpoints import users, node, flow, workspace,integrations
router = APIRouter()
router.include_router(users.router)
router.include_router(node.router)
router.include_router(flow.router)
router.include_router(workspace.router)
router.include_router(integrations.router)