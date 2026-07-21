from fastapi import APIRouter

from app.presentation.api.v1 import auth, health, telegram, users, verifications
from app.presentation.api.v1.admin.router import router as admin_router

router = APIRouter(prefix="/api/v1")
router.include_router(admin_router)
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(verifications.router)
router.include_router(telegram.router)
