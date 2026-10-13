"""סכמות קלט להרשמה והתחברות. ולידציה בלבד, בלי חוקים של האגרגט."""

from uuid import UUID

from goalvest_core.accounts import password_is_valid
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RegisterBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    full_name: str = Field(alias="fullName")
    email: str
    phone: str
    password: str
    role: str
    institution_id: UUID | None = Field(default=None, alias="institutionId")
    license_no: str | None = Field(default=None, alias="licenseNo")

    @field_validator("full_name", "phone", "license_no", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("email")
    @classmethod
    def email_shape(cls, value: str) -> str:
        cleaned = value.strip()
        if "@" not in cleaned or cleaned.startswith("@") or "." not in cleaned.split("@")[-1]:
            raise ValueError("כתובת האימייל אינה תקינה")
        return cleaned

    @field_validator("full_name")
    @classmethod
    def name_present(cls, value: str) -> str:
        if len(value) < 2:
            raise ValueError("יש להזין שם מלא")
        return value

    @field_validator("phone")
    @classmethod
    def phone_present(cls, value: str) -> str:
        digits = [ch for ch in value if ch.isdigit()]
        if len(digits) < 9:
            raise ValueError("מספר הטלפון אינו תקין")
        return value

    @field_validator("password")
    @classmethod
    def password_policy(cls, value: str) -> str:
        if not password_is_valid(value):
            raise ValueError("הסיסמה חייבת להכיל לפחות 8 תווים, אות ומספר")
        return value

    @field_validator("role")
    @classmethod
    def known_role(cls, value: str) -> str:
        if value not in ("INVESTOR", "AGENT"):
            raise ValueError("יש לבחור משקיע או סוכן")
        return value

    @model_validator(mode="after")
    def role_fields(self) -> "RegisterBody":
        if self.role == "AGENT":
            if self.institution_id is None:
                raise ValueError("יש לבחור גוף פיננסי")
            if not self.license_no:
                raise ValueError("יש להזין מספר רישיון")
        elif self.institution_id is not None or self.license_no:
            raise ValueError("משקיע אינו משויך לגוף פיננסי")
        return self


class LoginBody(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_present(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("יש להזין אימייל")
        return value

    @field_validator("password")
    @classmethod
    def password_present(cls, value: str) -> str:
        if not value:
            raise ValueError("יש להזין סיסמה")
        return value


class RefreshBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    refresh_token: str = Field(alias="refreshToken")
