from aiogram import Dispatcher, types
from aiogram.types import InputFile, ContentType
from aiogram.dispatcher import FSMContext
from openpyxl import Workbook
from openpyxl.styles import Font

from tg_bot.keyboards import start_admin_kb
from tg_bot.DBSM import all_user, Stats, process_referal_table, get_ref_balance_by_username
from tg_bot.states import Admin



def register_admin_handlers(dp: Dispatcher):
    dp.register_message_handler(cmd_start_admin, lambda message: str(message.from_user.id) in message.bot['config'].tg_bot.admin_ids, commands = ['admin'], state = "*")
    dp.register_callback_query_handler(admin_actions, text_startswith = "admin_")
    dp.register_message_handler(rass_text, state = Admin.rassylka, content_types= ContentType.ANY)
    dp.register_message_handler(process_check, state = Admin.check)


async def cmd_start_admin(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Здравствуйте! Добро пожаловать в админ-панель <b>BIO ACTIVE</b>\n\nВыберите интересующее действие в меню 👇", reply_markup= start_admin_kb())


async def admin_actions(call: types.CallbackQuery, state: FSMContext):
    action = call.data.split("_")[1]
    match action:
        case "rass":
            await call.message.answer("Отправьте мне сообщение для рассылки\n\nP.S. <u>Сообщение будет разослано в том виде, в котором вы его отправите, то есть вы можете рассылать не только текст, но и фотографии, видео и другие вложения!</u>")
            await Admin.rassylka.set()
        
        case "stats":
            stats = Stats()
            data = await stats.get_all_stats()
            await call.message.answer(f"📊 Статистика по пользователям бота:\n\n👤 Всего пользователей: <b>{data['all']}</b>\n🔗 Пришло по реф. ссылкам: <b>{data['all_ref']}</b>\n\n📅 Пришло сегодня: <b>{data['today']}</b>\n📅 Пришло в эту неделю: <b>{data['week']}</b>\n📅 Пришло в этот месяц: <b>{data['month']}</b>")
        
        case "table":
            waitmsg = await call.message.answer("Готовлю таблицу Excel, ожидайте...")
            await generate_data_table()
            await call.message.answer_document(document= InputFile("Реферальная статистика.xlsx"))
            await waitmsg.delete()
        
        case "check":
            await call.message.answer("Введите юзернейм пользователя, баланс реферального кабинета которого Вы хотите проверить 👇")
            await Admin.check.set()


async def rass_text(message: types.Message, state: FSMContext):
    count = 0
    for i in await all_user():
        try:
            await message.send_copy(chat_id = i.user_id)
            count += 1
        except:
            pass

    await message.answer(f"Разослано сообщений: <b>{count} шт.</b>")
    await state.finish()


async def process_check(message: types.Message, state: FSMContext):
    res = await get_ref_balance_by_username(message.text.replace("@", ""))
    await message.answer(res)
    await state.finish()


async def generate_data_table():
    data = await process_referal_table()
    wb = Workbook()
    wb.remove(wb["Sheet"])
    sheet = wb.create_sheet("Балансы", 0)

    sheet["A1"] = "Юзернейм"
    sheet['A1'].font = Font(color="FF0000")  
    sheet["B1"] = "Баланс"
    sheet['B1'].font = Font(color="FF0000")  


    for i in range(len(data)):
        sheet[f"A{i+2}"] = f"@{data[i].username}"
        sheet[f"B{i+2}"] = f"{data[i].referal_balance}₽"
    
    wb.save("Реферальная статистика.xlsx")