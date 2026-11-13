from fastapi import APIRouter

from app.api.v1 import auth, certificates, verify

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(certificates.router)
api_router.include_router(verify.router)
api_router.include_router(verify.verifications_router)

# Remaining Tier 1 routers are mounted here as they land:
#   institutions, reviews, share, admin
