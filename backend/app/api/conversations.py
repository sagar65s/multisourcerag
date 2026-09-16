from fastapi import APIRouter, Depends, Query, Response, status

from app.core.security import AuthenticatedUser, current_user
from app.database.mongodb import get_database
from app.repositories.conversations import ConversationRepository
from app.schemas.chat import ConversationRename, ConversationView, MessageView
from app.services.audit_service import audit_event

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationView])
async def list_conversations(search: str | None = Query(default=None, max_length=100), limit: int = Query(default=50, ge=1, le=100), skip: int = Query(default=0, ge=0), user: AuthenticatedUser = Depends(current_user)) -> list[ConversationView]:
    return await ConversationRepository(get_database()).list_owned(user.uid, search, limit, skip)


@router.get("/{conversation_id}", response_model=ConversationView)
async def get_conversation(conversation_id: str, user: AuthenticatedUser = Depends(current_user)) -> ConversationView:
    return ConversationRepository.conversation_view(await ConversationRepository(get_database()).get_owned(user.uid, conversation_id))


@router.get("/{conversation_id}/messages", response_model=list[MessageView])
async def list_messages(conversation_id: str, user: AuthenticatedUser = Depends(current_user)) -> list[MessageView]:
    return await ConversationRepository(get_database()).list_messages(user.uid, conversation_id)


@router.patch("/{conversation_id}", response_model=ConversationView)
async def rename_conversation(conversation_id: str, payload: ConversationRename, user: AuthenticatedUser = Depends(current_user)) -> ConversationView:
    return await ConversationRepository(get_database()).rename(user.uid, conversation_id, payload.title)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: str, user: AuthenticatedUser = Depends(current_user)) -> Response:
    await ConversationRepository(get_database()).delete(user.uid, conversation_id); await audit_event(user.uid, "conversation_delete", resource_type="conversation", resource_id=conversation_id); return Response(status_code=status.HTTP_204_NO_CONTENT)
