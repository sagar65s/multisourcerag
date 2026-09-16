from fastapi import APIRouter

from app.api import account, admin, chat, conversations, dashboard, documents, exports, health, intelligence, jobs, research, saved, websites, workspaces

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(dashboard.router)
api_router.include_router(workspaces.router)
api_router.include_router(chat.router)
api_router.include_router(documents.router)
api_router.include_router(websites.router)
api_router.include_router(research.router)
api_router.include_router(intelligence.router)
api_router.include_router(conversations.router)
api_router.include_router(saved.router)
api_router.include_router(exports.router)
api_router.include_router(account.router)
api_router.include_router(jobs.router)
api_router.include_router(admin.router)
