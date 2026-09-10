from fastapi import APIRouter

from app.api.v1.endpoints import auth, favorites, matches, subscriptions, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(matches.router)
api_router.include_router(favorites.router)
api_router.include_router(subscriptions.router)
