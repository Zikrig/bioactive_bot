from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def start_admin_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text = "📨 Рассылка", callback_data= "admin_rass"))
    kb.add(InlineKeyboardButton(text = "📊 Статистика", callback_data= "admin_stats"))
    kb.add(InlineKeyboardButton(text = "📄 Выгрузка данных", callback_data= "admin_table"))
    kb.add(InlineKeyboardButton(text = "💰 Проверить баланс", callback_data= "admin_check"))
    return kb

def contact_kb(username):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text = "💬 Связаться с заказчиком", url = f"https://t.me/{username}"))
    return kb