from app.api.account import has_recent_auth

def test_recent_auth_accepts_fresh_login():
    assert has_recent_auth(950, 1000)

def test_recent_auth_rejects_old_or_missing_login():
    assert not has_recent_auth(399, 1000)
    assert not has_recent_auth(0, 1000)
