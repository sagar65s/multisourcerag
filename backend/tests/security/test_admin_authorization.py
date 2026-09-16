import pytest
from fastapi import HTTPException

from app.core.security import AuthenticatedUser, admin_user


@pytest.mark.asyncio
async def test_non_admin_is_denied():
    with pytest.raises(HTTPException) as error:
        await admin_user(AuthenticatedUser(uid="user-a", email=None, is_admin=False))
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_admin_claim_is_required_and_accepted():
    user = AuthenticatedUser(uid="admin-a", email=None, is_admin=True)
    assert await admin_user(user) == user
