from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def start_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text = "💬 Наш чат", url = "https://t.me/+sgdW0P9e9u9jMTcy"))
    kb.add(InlineKeyboardButton(text = "📢 Наш канал", url = "https://t.me/+daOm2Fv5FTBkMmNi"))
    kb.add(InlineKeyboardButton(text = "🏠 В главное меню", callback_data= "start_back"))
    return kb

def main_kb(has_referal_access: bool = False):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text = "📌 Про наши пептиды", callback_data= "start_about"))
    kb.add(InlineKeyboardButton(text = "🛒 Каталог пептидов", callback_data= "start_catalog"))
    kb.add(InlineKeyboardButton(text = "🤖 ИИ-ассистент", callback_data= "start_ai"))
    if has_referal_access:
        kb.add(InlineKeyboardButton(text = "💰 Реферальный кабинет", callback_data= "start_referal"))
    kb.add(InlineKeyboardButton(text = "📄 Публичная Оферта", url = "https://disk.yandex.ru/i/tINnw4jOFwwhcA"))
    kb.add(InlineKeyboardButton(text = "💬 Наш чат", url = "https://t.me/+sgdW0P9e9u9jMTcy"))
    kb.add(InlineKeyboardButton(text = "📢 Наш канал", url = "https://t.me/+daOm2Fv5FTBkMmNi"))
    kb.add(InlineKeyboardButton(text = "🌐 Веб-сайт", url = "https://bioactive.pro/"))
    return kb

def about_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text = "🏢 О компании", callback_data= "about_company"))
    kb.add(InlineKeyboardButton(text = "💊 Продукт", callback_data= "about_product"))
    kb.add(InlineKeyboardButton(text = "❓ Что такое пептиды?", callback_data= "about_what"))
    kb.add(InlineKeyboardButton(text = "🤔 Почему наши пептиды?", callback_data= "about_why"))
    kb.add(InlineKeyboardButton(text = "📄 Документы", callback_data= "about_docs"))
    kb.add(InlineKeyboardButton(text = "🔍 Вопрос-ответ", callback_data= "about_quest"))
    kb.add(InlineKeyboardButton(text = "💡 Экспертное мнение", callback_data= "about_expert"))
    kb.add(InlineKeyboardButton(text = "⭐ История успеха", callback_data= "about_success"))
    kb.add(InlineKeyboardButton(text = "🏠 В главное меню", callback_data= "start_back"))
    return kb

def toabout_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text = "🔙 Назад", callback_data= "about_back"))
    return kb

def back_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text = "🏠 В главное меню", callback_data= "start_back"))
    return kb

def referal_kb(link):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text = "📤 Поделиться", switch_inline_query=link))
    kb.add(InlineKeyboardButton(text = "💸 Заявка на вывод", callback_data= "payoff"))
    kb.add(InlineKeyboardButton(text = "🏠 В главное меню", callback_data= "start_back"))
    return kb

def catalog_kb(pos: int, is_first: bool, is_last: bool):
    kb = InlineKeyboardMarkup()
    if not is_last:
        kb.add(InlineKeyboardButton(text = "➡️ Вперёд", callback_data= f"slide_{pos}_1"))
    if not is_first:
        kb.add(InlineKeyboardButton(text = "⬅️ Назад", callback_data= f"slide_{pos}_0"))

    kb.add(InlineKeyboardButton(text = "➕ В корзину", callback_data= f"addtobucket_{pos}"))
    kb.add(InlineKeyboardButton(text = "💵 Стоимость", callback_data= "start_price"))
    kb.add(InlineKeyboardButton(text = "🛒 Моя корзина", callback_data= "start_bucket"))
    kb.add(InlineKeyboardButton(text = "🤖 Консультация", callback_data= "start_ai"))
    kb.add(InlineKeyboardButton(text = "🏠 В главное меню", callback_data= "start_back"))
    return kb

def close_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text = "❌ Закрыть", callback_data= "start_close"))
    return kb

def bucket_kb(price: int, is_clear: bool):
    kb = InlineKeyboardMarkup()
    if not is_clear:
        kb.add(InlineKeyboardButton(text = "🧹 Очистить", callback_data= "clear_bucket"))
        kb.add(InlineKeyboardButton(text = "✅ Оформить заказ", callback_data= f"pay_{price}"))
        kb.add(InlineKeyboardButton(text = "📄 Публичная Оферта", url = "https://disk.yandex.ru/i/tINnw4jOFwwhcA"))
        kb.add(InlineKeyboardButton(text = "❌ Закрыть", callback_data= "start_close"))
    else:
        kb.add(InlineKeyboardButton(text = "🛒 Открыть каталог", callback_data= "start_catalog"))
        kb.add(InlineKeyboardButton(text = "🏠 В главное меню", callback_data= "start_back"))
    return kb

def pay_kb(pay_link: str):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text = "💳 Оплатить", url = pay_link))
    kb.add(InlineKeyboardButton(text = "📄 Публичная Оферта", url = "https://disk.yandex.ru/i/tINnw4jOFwwhcA"))
    kb.add(InlineKeyboardButton(text = "🛒 Моя корзина", callback_data= "start_bucket"))
    return kb

def after_clear_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text = "🛒 Открыть каталог", callback_data= "start_catalog"))
    kb.add(InlineKeyboardButton(text = "🏠 В главное меню", callback_data= "start_back"))
    return kb

def watch_docs_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text = "📋 Декларация соответствия", callback_data= "docs_declaration"))
    kb.add(InlineKeyboardButton(text = "✅ Сертификат «Высшее качество» \"Халяль\"", callback_data= "docs_halal"))
    kb.add(InlineKeyboardButton(text = "🌿 Сертификат «Высшее качество» \"БИО Продукт\"", callback_data= "docs_bio"))
    kb.add(InlineKeyboardButton(text = "🔙 Назад", callback_data= "about_back"))
    return kb