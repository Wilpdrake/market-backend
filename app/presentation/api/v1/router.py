from fastapi import APIRouter

from app.presentation.api.v1 import auth, health, telegram, users, verifications

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(verifications.router)
router.include_router(telegram.router)
