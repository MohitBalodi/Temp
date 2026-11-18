from fastapi import APIRouter

from app.api.v1 import admin, auth, certificates, institutions, reviews, verify

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(institutions.router)
api_router.include_router(certificates.router)
api_router.include_router(verify.router)
api_router.include_router(verify.verifications_router)
api_router.include_router(reviews.router)
api_router.include_router(admin.router)

# Remaining routers are mounted here as they land:
#   share
