from datetime import datetime

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AccountDeleteRequest(BaseModel):
    confirmation: str = Field(pattern="^DELETE$")


class AccountView(BaseModel):
    uid: str
    email: str | None = None
    display_name: str | None = None
    photo_url: str | None = None
    provider: str | None = None
    email_verified: bool = False
    is_admin: bool = False
    created_at: datetime
    last_login_at: datetime


class UserSettingsView(BaseModel):
    theme: Literal["light", "dark", "system"] = "system"
    language: Literal["English", "Tamil", "Hindi"] = "English"
    updated_at: datetime


class UserSettingsUpdate(BaseModel):
    theme: Literal["light", "dark", "system"] | None = None
    language: Literal["English", "Tamil", "Hindi"] | None = None

    @model_validator(mode="after")
    def require_change(self) -> "UserSettingsUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one setting is required")
        return self
