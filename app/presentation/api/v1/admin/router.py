from fastapi import APIRouter

from app.presentation.api.v1.admin import audit, auth, crm, products, settings, tags, users

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(products.router)
router.include_router(tags.router)
router.include_router(crm.router)
router.include_router(audit.router)
router.include_router(settings.router)
