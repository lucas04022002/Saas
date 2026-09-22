from fastapi import APIRouter

from app.api.v1.endpoints import auth, bankroll, billing, books, favorites, matches, track_record, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(matches.router)
api_router.include_router(books.router)
api_router.include_router(bankroll.router)
api_router.include_router(track_record.router)
api_router.include_router(favorites.router)
api_router.include_router(billing.router)
