from aiogram.fsm.state import State, StatesGroup


class ProjectCreationState(StatesGroup):
    """
    States used during project creation.
    """

    waiting_for_name = State()
    waiting_for_database_path = State()
    waiting_for_media_path = State()
    waiting_for_schedule = State()
    waiting_for_confirmation = State()
