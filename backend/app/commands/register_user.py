"""RegisterUser – יצירת UserRegistered. ה-Handler מחזיר id ו-version בלבד."""

from dataclasses import dataclass
from uuid import UUID

from goalvest_core import EmailAlreadyExists
from goalvest_core.accounts import UserAccount, normalize_email

from app.auth.errors import UnknownInstitution
from app.auth.passwords import hash_password
from app.commands.bus import Command, CommandContext, CommandResult
from app.queries.users import email_exists
from app.reference.institutions import find_institution


@dataclass(frozen=True)
class RegisterUser(Command):
    email: str
    full_name: str
    phone: str
    password: str
    role: str
    institution_id: UUID | None = None
    license_no: str | None = None
    correlation_id: str | None = None


def handle_register_user(command: RegisterUser, ctx: CommandContext) -> CommandResult:
    email = normalize_email(command.email)
    if command.role == "AGENT" and (
        command.institution_id is None or find_institution(command.institution_id) is None
    ):
        raise UnknownInstitution()
    if email_exists(ctx.repository.session, email):
        raise EmailAlreadyExists()
    account = UserAccount()
    account.register(
        email=email,
        full_name=command.full_name,
        phone=command.phone,
        password=command.password,
        role=command.role,
        institution_id=command.institution_id,
        license_no=command.license_no,
        hash_password=hash_password,
        metadata={
            "user_id": str(account.aggregate_id),
            "role": command.role,
            "correlation_id": command.correlation_id,
            "command_id": str(command.command_id),
        },
    )
    ctx.repository.append(account.aggregate_id, 0, account.uncommitted_events)
    return CommandResult(id=account.aggregate_id, version=account.version)
