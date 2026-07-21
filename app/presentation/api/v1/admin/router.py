from fastapi import APIRouter

from app.presentation.api.v1.admin import auth, products, users

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(products.router)
