"""חיבור הפקודה, ה-projector וה-bus לבקשה."""

from sqlalchemy.orm import Session

from app.commands.bus import CommandBus
from app.commands.register_user import RegisterUser, handle_register_user
from app.projections.dispatcher import ProjectionDispatcher
from app.projections.users import project_user_registered


def build_dispatcher() -> ProjectionDispatcher:
    dispatcher = ProjectionDispatcher()
    dispatcher.register("UserRegistered", project_user_registered)
    return dispatcher


def build_command_bus(session: Session, dispatcher: ProjectionDispatcher) -> CommandBus:
    bus = CommandBus(session, dispatcher)
    bus.register(RegisterUser, handle_register_user)
    return bus
