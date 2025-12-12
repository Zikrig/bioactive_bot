from aiogram.dispatcher.filters.state import State, StatesGroup

class User(StatesGroup):
    ...

class Admin(StatesGroup):
    rassylka = State()
    check = State()