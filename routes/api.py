from fastapi import APIRouter
from src.endpoints import users, node, flow, workspace,integrations,customfields
# from src.dependencies.config import ROUTE_PREFIX_V1
router = APIRouter()
router.include_router(users.router)
router.include_router(node.router)
router.include_router(flow.router)
router.include_router(workspace.router)
router.include_router(integrations.router)
router.include_router(customfields.router)


# def include_api_routes():
#     ''' Include to router all api rest routes with version prefix '''
#     router.include_router(users.router,prefix=ROUTE_PREFIX_V1)
#     router.include_router(node.router, prefix=ROUTE_PREFIX_V1)
#     router.include_router(flow.router, prefix=ROUTE_PREFIX_V1)
#     router.include_router(workspace.router, prefix=ROUTE_PREFIX_V1)
#     router.include_router(integrations.router, prefix=ROUTE_PREFIX_V1)
#     router.include_router(customfields.router, prefix=ROUTE_PREFIX_V1)

# include_api_routes()