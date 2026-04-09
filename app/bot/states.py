from aiogram.fsm.state import State, StatesGroup


class OnboardingState(StatesGroup):
    answering = State()


class MealClarificationState(StatesGroup):
    answering = State()


class ReminderState(StatesGroup):
    waiting_time = State()
