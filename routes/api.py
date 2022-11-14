from fastapi import APIRouter
from src.endpoints import (
    users,
    node,
    flow,
    workspace,
    integrations,
    customfields,
    livechat,
)
from src.dependencies.config import VERSION_PREFIX

router = APIRouter()
# router.include_router(users.router)
# router.include_router(node.router)
# router.include_router(flow.router)
# router.include_router(workspace.router)
# router.include_router(integrations.router)
# router.include_router(customfields.router)


def include_api_routes():
    """Include to router all api rest routes with version prefix"""
    router.include_router(users.router, prefix=VERSION_PREFIX)
    router.include_router(node.router, prefix=VERSION_PREFIX)
    router.include_router(flow.router, prefix=VERSION_PREFIX)
    router.include_router(workspace.router, prefix=VERSION_PREFIX)
    router.include_router(integrations.router, prefix=VERSION_PREFIX)
    router.include_router(customfields.router, prefix=VERSION_PREFIX)
    router.include_router(livechat.router, prefix=VERSION_PREFIX)


include_api_routes()
