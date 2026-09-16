from fastapi import APIRouter, Depends, Query, Response, status

from app.core.security import AuthenticatedUser, current_user
from app.database.mongodb import get_database
from app.repositories.saved import SavedRepository
from app.schemas.chat import BookmarkCreate, BookmarkView, FeedbackCreate, SavedAnswerCreate, SavedAnswerView

router = APIRouter(tags=["saved and feedback"])


@router.post("/saved", response_model=SavedAnswerView, status_code=status.HTTP_201_CREATED)
async def save_answer(payload: SavedAnswerCreate, user: AuthenticatedUser = Depends(current_user)) -> SavedAnswerView:
    return await SavedRepository(get_database()).save_answer(user.uid, payload.message_id)


@router.get("/saved", response_model=list[SavedAnswerView])
async def list_saved(limit: int = Query(default=50, ge=1, le=100), skip: int = Query(default=0, ge=0), user: AuthenticatedUser = Depends(current_user)) -> list[SavedAnswerView]:
    return await SavedRepository(get_database()).list_answers(user.uid, limit, skip)


@router.delete("/saved/{saved_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved(saved_id: str, user: AuthenticatedUser = Depends(current_user)) -> Response:
    await SavedRepository(get_database()).delete_answer(user.uid, saved_id); return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/bookmarks", response_model=BookmarkView, status_code=status.HTTP_201_CREATED)
async def create_bookmark(payload: BookmarkCreate, user: AuthenticatedUser = Depends(current_user)) -> BookmarkView:
    return await SavedRepository(get_database()).bookmark(user.uid, payload.message_id, payload.source_id, payload.note)


@router.get("/bookmarks", response_model=list[BookmarkView])
async def list_bookmarks(limit: int = Query(default=50, ge=1, le=100), skip: int = Query(default=0, ge=0), user: AuthenticatedUser = Depends(current_user)) -> list[BookmarkView]:
    return await SavedRepository(get_database()).list_bookmarks(user.uid, limit, skip)


@router.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(bookmark_id: str, user: AuthenticatedUser = Depends(current_user)) -> Response:
    await SavedRepository(get_database()).delete_bookmark(user.uid, bookmark_id); return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/messages/{message_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def submit_feedback(message_id: str, payload: FeedbackCreate, user: AuthenticatedUser = Depends(current_user)) -> Response:
    await SavedRepository(get_database()).feedback(user.uid, message_id, payload); return Response(status_code=status.HTTP_204_NO_CONTENT)
