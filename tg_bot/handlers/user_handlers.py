from aiogram import Dispatcher, types
from aiogram.types import InputFile, InputMediaPhoto
from aiogram.dispatcher import FSMContext
from aiogram.utils.deep_linking import decode_payload, get_start_link

from tg_bot.keyboards import start_kb, main_kb, about_kb, toabout_kb, back_kb, referal_kb, catalog_kb, close_kb, bucket_kb, pay_kb, contact_kb, after_clear_kb, watch_docs_kb
from tg_bot.DBSM import add_user, is_invited, get_referal_level, get_referals_count, get_referal_balance, add_to_bucket, bucket_items, clear_bucket, process_referal_up, MAIN_REFERAL_ID, create_pay
from tg_bot.robokassa import generate_payment_link

import json
import asyncio
import os

def decline_users(n):
    last_digit = n % 10
    second_last_digit = (n // 10) % 10
    
    if second_last_digit == 1:
        return f"{n} пользователей"
    
    if last_digit == 1:
        return f"{n} пользователь"
    elif last_digit in [2, 3, 4]:
        return f"{n} пользователя"
    else:
        return f"{n} пользователей"
    


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(cmd_start, commands= ['start'], state = "*")
    dp.register_callback_query_handler(start_actions, text_startswith = "start_")
    dp.register_callback_query_handler(about_actions, text_startswith = "about_")
    dp.register_callback_query_handler(docs_actions, text_startswith = "docs_")
    dp.register_callback_query_handler(payoff_application, text = "payoff")
    dp.register_callback_query_handler(process_slide, text_startswith = "slide_")
    dp.register_callback_query_handler(process_add, text_startswith = "addtobucket_")
    dp.register_callback_query_handler(start_pay, text_startswith = "pay_")
    dp.register_callback_query_handler(proc_clear_bucket, text = "clear_bucket")
    dp.register_callback_query_handler(payed, text_startswith = "payed_")
    dp.register_message_handler(ai_response)



async def ai_response(message: types.Message, state: FSMContext):
    rag_system = message.bot['rag_system']
    waitmsg = await message.reply("⏳ Генерирую ответ, ожидайте...")
    response = await rag_system.generate_response(message.text)
    await waitmsg.delete()
    await message.reply(response[0])


async def cmd_start(message: types.Message, state: FSMContext):
    if not message.from_user.username:
        return await message.answer("⛔ Для корректного использования нашего бота просим Вас установить юзернейм (имя пользователя) в Telegram.")
    
    referal_id = int(decode_payload(message.get_args())) if message.get_args() else MAIN_REFERAL_ID
    await state.finish()

    if await add_user(message.from_user.username, message.from_user.id, referal_id):
        # Уведомляем реферала только о НОВЫХ пользователях
        if message.get_args():
            await message.bot.send_message(chat_id=referal_id, text=f"🎉 Новый пользователь @{message.from_user.username} зашел по Вашей реферальной ссылке!")
        await message.answer("👋 Здравствуйте!\nДобро пожаловать в <b>BIO ACTIVE</b>.\n\n✨ Откройте для себя современные пищевые добавки на основе пептидов для восстановления и обновления организма без лишних рисков и побочных эффектов.\n\n🌷 Присоединяйтесь к нашему Telegram-каналу, чтобы узнать больше о пептидах и пообщаться с единомышленницами!", reply_markup= start_kb())
    else:
        # Пользователь уже зарегистрирован — показываем обычное меню
        referal_level = await get_referal_level(message.from_user.id)
        has_referal_access = referal_level in ['first', 'second']
        await message.answer("👋 Здравствуйте! Добро пожаловать в <b>BIO ACTIVE</b>\n\nВыберите интересующий вас раздел в меню 👇", reply_markup= main_kb(has_referal_access))
    

async def start_actions(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    action = call.data.split("_")[1]
    
    # Проверяем, является ли пользователь рефералом (первого или второго уровня)
    referal_level = await get_referal_level(call.from_user.id)
    has_referal_access = referal_level in ['first', 'second']  # Рефералы 1 и 2 уровня имеют доступ
    
    match action:
        case "back":
            if call.message.text:
                await call.message.edit_text("👋 Здравствуйте! Добро пожаловать в <b>BIO ACTIVE</b>\n\nВыберите интересующий вас раздел в меню 👇", reply_markup= main_kb(has_referal_access))
            else:
                await call.message.answer("👋 Здравствуйте! Добро пожаловать в <b>BIO ACTIVE</b>\n\nВыберите интересующий вас раздел в меню 👇", reply_markup= main_kb(has_referal_access))
                await call.message.delete()
        
        case "about":
            await call.message.edit_text("⭐ Откройте для себя настоящую революцию в уходе за собой — пептидные добавки BIO ACTIVE.\n\n💎 Пептиды — это не просто модный тренд, а ключ к обновлению и молодости вашего организма. Они “разговаривают” с клетками, запускают процессы восстановления и помогают сохранить здоровье без побочных эффектов.\n\n✨ Наши продукты созданы для женщин, которые хотят быть энергичными, красивыми и уверенными в себе.\nЗдесь вы найдёте решения для поддержки женского здоровья, молодости кожи, гармонии гормонов и жизненного тонуса.\n\nВыберите интересующий вас раздел в меню 👇", reply_markup= about_kb())

        case "ai":
            await call.message.answer("🤖 Если Вы хотите проконсультироваться с нашим умным ИИ-ассистентом, то просто напишите сообщение боту, и Ваш запрос будет сразу же обработан!", reply_markup= close_kb())

        case "referal":
            link = await get_start_link(call.from_user.id, encode=True)
            users_count = decline_users(await get_referals_count(call.from_user.id))
            balance = await get_referal_balance(call.from_user.id)
            
            # Определяем уровень реферала и показываем соответствующее описание
            referal_level = await get_referal_level(call.from_user.id)
            
            if referal_level == 'first':
                # Реферал первого уровня (case 1 или 2)
                referal_info = f"""👤 <u>Реферальный кабинет</u>

💵 Благодаря нашей реферальной системе вы можете зарабатывать деньги, приглашая пользователей в бота <b>BIO ACTIVE</b>

💎 <b>Ваши условия как реферала первого уровня:</b>
• 🥇 <b>50%</b> от покупок всех приглашенных вами пользователей
• 🥈 <b>10%</b> от покупок рефералов второго уровня (которых пригласили ваши рефералы)
   <i>Реферал второго уровня сам получает 40% от этих покупок</i>

<i>📊 Пример:
Вы пригласили Алексея → он купил на 10,000₽ → вы получаете 5,000₽ (50%)
Алексей пригласил Марию → она купила на 10,000₽ → Алексей получает 4,000₽ (40%), вы получаете 1,000₽ (10%)</i>

🔗 Ваша реферальная ссылка (нажмите на неё, и она скопируется автоматически!):
<code>{link}</code>

👥 Вами уже приглашено: <i>{users_count}</i>

💳 Ваш баланс реферального кабинета: <b>{balance}</b>"""
            
            elif referal_level == 'second':
                # Реферал второго уровня
                referal_info = f"""👤 <u>Реферальный кабинет</u>

💵 Благодаря нашей реферальной системе вы можете зарабатывать деньги, приглашая пользователей в бота <b>BIO ACTIVE</b>

💎 <b>Ваши условия как реферала второго уровня:</b>
• 🥈 <b>40%</b> от покупок всех приглашенных вами пользователей

<i>📊 Пример:
Вы пригласили Марию → она купила на 10,000₽ → вы получаете 4,000₽ (40%)</i>

🔗 Ваша реферальная ссылка (нажмите на неё, и она скопируется автоматически!):
<code>{link}</code>

👥 Вами уже приглашено: <i>{users_count}</i>

💳 Ваш баланс реферального кабинета: <b>{balance}</b>"""
            
            await call.message.edit_text(referal_info, reply_markup= referal_kb(link))

        case "catalog":
            await process_catalog(call.message, 1)

        case "price":
            await call.message.answer("Стоимость пептидов <b>BIO ACTIVE</b>:\n<b>1</b> флакон - <b>6900₽</b>\n<b>3</b> флакона - <b>19500₽</b>\n<b>6</b> флаконов - <b>36000₽ + один в подарок</b>\n\n<i>Комплексы могут формироваться из любых пептидов на ваш выбор</i>", reply_markup= close_kb())

        case "bucket":
            text, price, is_clear = await bucket_items(call.from_user.id)
            if call.message.caption:
                await call.message.answer(text, reply_markup= bucket_kb(price, is_clear))
            else:
                await call.message.edit_text(text, reply_markup= bucket_kb(price, is_clear))

        case "close":
            await call.message.delete()

        


async def about_actions(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    action = call.data.split("_")[1]
    match action:
        case "back":
            if call.message.text:
                await call.message.edit_text("⭐ Откройте для себя настоящую революцию в уходе за собой — пептидные добавки BIO ACTIVE.\n\n💎 Пептиды — это не просто модный тренд, а ключ к обновлению и молодости вашего организма. Они “разговаривают” с клетками, запускают процессы восстановления и помогают сохранить здоровье без побочных эффектов.\n\n✨ Наши продукты созданы для женщин, которые хотят быть энергичными, красивыми и уверенными в себе.\nЗдесь вы найдёте решения для поддержки женского здоровья, молодости кожи, гармонии гормонов и жизненного тонуса.\n\nВыберите интересующий вас раздел в меню 👇", reply_markup= about_kb())
            else:
                await call.message.answer("⭐ Откройте для себя настоящую революцию в уходе за собой — пептидные добавки BIO ACTIVE.\n\n💎 Пептиды — это не просто модный тренд, а ключ к обновлению и молодости вашего организма. Они “разговаривают” с клетками, запускают процессы восстановления и помогают сохранить здоровье без побочных эффектов.\n\n✨ Наши продукты созданы для женщин, которые хотят быть энергичными, красивыми и уверенными в себе.\nЗдесь вы найдёте решения для поддержки женского здоровья, молодости кожи, гармонии гормонов и жизненного тонуса.\n\nВыберите интересующий вас раздел в меню 👇", reply_markup= about_kb())
                await call.message.delete()

        case "what":
            await call.message.edit_text("В каждом флаконе BIO ACTIVE — не просто жидкость, а концентрат современной науки и природы.\n\n<b>В основе наших продуктов:</b>\n• Особые пептиды — короткие цепочки аминокислот, которые выступают в организме “сигналами” для клеток: запускают обновление, восстановление и защиту.\n• Флуревиты — стерильные водные растворы с низкими концентрациями белково-пептидных соединений. Их получают из тканей животных, растений или грибов — это источник жизненной силы для клеток.\n• Нет аллергенов, гормонов, искусственных добавок и тяжёлых консервантов.\n\n<b>Как это работает?</b>\nПептиды и флуревиты действуют мягко и адресно, “разговаривая” с определёнными тканями (например, кожей, суставами, эндометрием). Они активируют природные механизмы восстановления — организм сам начинает обновлять клетки, усиливать защиту, замедлять процессы старения.\n\n<b>Почему это безопасно?</b>\n— Не вызывает побочных эффектов\n— Не даёт нагрузку на печень и почки\n— Можно сочетать с любыми привычными средствами\n— Даже при ошибочном диагнозе не навредит — пептиды работают только там, где это действительно нужно\n\n<b>BIO ACTIVE — это натуральный, научно продуманный состав, который помогает вашему организму вернуть энергию, молодость и внутренний баланс.</b>", reply_markup= toabout_kb())

        case "company":
            await call.message.edit_text("<b>🏢 О компании BIO ACTIVE</b>\n\nBIO ACTIVE стремительно развивается на рынке более двух лет и уже успела зарекомендовать себя как уникальный производитель товаров для репродуктивного здоровья и не только. Мы специализируемся на создании продуктов на основе инновационных полипептидов, не имеющих аналогов.", reply_markup= toabout_kb())
        
        case "product":
            await call.message.edit_text("<b>💊 Пептиды BIO ACTIVE</b>\n\nПептиды — это краткие цепочки аминокислот, играющие важную роль в регуляции процессов в организме. В последние годы они приобрели популярность благодаря своим свойствам, которые способствуют восстановлению и поддержанию здоровья на клеточном уровне.\n\n<b>Уникальность пептидных соединений</b>\n\nBIO ACTIVE предлагает высококачественные пептиды, которые активируют процессы самоисцеления в организме. Наши продукты основаны на передовых технологиях извлечения белковых соединений и обладают высокой биодоступностью, что делает их эффективными в борьбе с различными заболеваниями.\n\n<b>Механизм действия</b>\n\nПептиды представляют собой строительные элементы, которые восстанавливают клетки и ткани, улучшая их функции. Они действуют как регуляторы различных биохимических процессов, поддерживая здоровье органов и тканей и обеспечивая передачу сигналов, необходимых для правильной работы системы.\n\nГлавное отличие пептидов от традиционных лекарственных препаратов заключается в том, что они не просто устраняют симптомы, а работают над восстановлением естественного механизма функционирования организма. Это приводит к долговременному оздоровлению и омоложению на клеточном уровне.\n\n<b>Преимущества использования пептидов</b>\n\n1. <b>Безопасность:</b> Пептиды не вызывают побочных эффектов и могут использоваться даже при ошибочном диагнозе.\n2. <b>Профилактика:</b> Идеальны для использования в качестве профилактического средства, что делает их отличным выбором для поддержания здоровья.\n3. <b>Комбинирование:</b> Пептиды можно принимать совместно с другими биопрепаратами и лекарственными средствами, что усиливает их эффект.\n\nBIO ACTIVE предлагает инновационные решения в области здоровья через использование пептидов. Мы стремимся помочь каждому клиенту достигнуть гармонии между физическим и эмоциональным состоянием, используя научно обоснованные и безопасные подходы к восстановлению и поддержанию здоровья. Присоединяйтесь к нам на пути к восстановлению здоровья на глубоком уровне!", reply_markup= toabout_kb())

        case "why":
            await call.message.edit_text("<b>В каждом флаконе BIO ACTIVE — то, что выгодно отличает нас от других:</b>\n\n<b>• Природный состав и чистота:</b>\nВ основе BIO ACTIVE — особые пептидные комплексы и флуревиты из тщательно отобранных природных источников. Мы не используем гормоны, аллергенные компоненты или тяжёлые консерванты. Только то, что действительно работает на обновление организма.\n\n<b>• Точечное и деликатное действие:</b>\nНаши пептиды запускают процессы восстановления именно в тех тканях и системах, которым требуется поддержка: кожа, суставы, женское и мужское здоровье, иммунитет, нервная система. BIO ACTIVE не вмешивается в лишние процессы, а мягко стимулирует естественные механизмы обновления там, где это важно для вашего здоровья и самочувствия.\n\n<b>• Максимальная безопасность:</b>\nВ отличие от многих других добавок, BIO ACTIVE не перегружает организм, не вызывает побочных эффектов, подходит даже для самых чувствительных и не способен навредить даже при длительном применении. Продукты можно безопасно сочетать с привычными средствами.\n\n<b>• Современный научный подход:</b>\nBIO ACTIVE создан на основе передовых исследований клеточного обновления. Мы не просто «добавляем» пептиды — мы помогаем вашему организму заново включить собственные ресурсы для восстановления, омоложения и защиты.\n\n<b>• Открытость и доверие:</b>\nМы всегда подробно рассказываем, что находится внутри каждого флакона и как это действует. BIO ACTIVE — это не случайная смесь, а продуманная формула с чётко доказанным механизмом.\n\n<b>BIO ACTIVE — это пептиды, которые работают для вас: мягко, точно и эффективно. Именно поэтому наши продукты выбирают снова и снова.</b>", reply_markup= toabout_kb())

        case "sucess":
            await call.message.bot.send_chat_action(chat_id= call.message.chat.id, action= "upload_video")
            await call.message.answer_video(video = InputFile("историяуспеха.mov", filename = "История успеха.mov"), height=1080, width=608, reply_markup= toabout_kb())
        
        case "docs":
            await call.message.edit_text(
                """✅ <b>Законность. Качество. Безопасность.</b>

Продукция <b>BIO ACTIVE</b> официально зарегистрирована и соответствует всем требованиям технических регламентов Таможенного союза (ЕАЭС).
На каждую позицию оформлены декларации о соответствии, подтверждающие:

Безопасность состава – в соответствии с ТР ТС 021/2011 (о безопасности пищевой продукции),

Качественную маркировку – по стандартам ТР ТС 022/2011,

Допустимость ингредиентов – согласно ТР ТС 029/2012 (пищевые добавки, ароматизаторы, технологические средства).

Продукция BIO ACTIVE прошла все необходимые испытания и получила сертификаты в соответствии со всеми требованиями, гарантируя партнёрам прозрачность поставок и уверенность в высоком стандарте продукции.""",
                reply_markup=watch_docs_kb()
            )

        case "watch":
            await call.message.answer_document(InputFile("tg_bot/data/sertificates/Декларация соответствия.pdf", "Декларация соответствия.pdf"), reply_markup=close_kb())
            await call.message.answer_document(InputFile("tg_bot/data/sertificates/ПИ к ДЕКЛАРАЦИИ.pdf", "ПИ к ДЕКЛАРАЦИИ.pdf"), reply_markup=close_kb())
            await call.message.answer_document(InputFile("tg_bot/data/sertificates/ПИ к сертификату соответствия БИО ПРОДУКТ.pdf", "ПИ к сертификату соответствия “БИО ПРОДУКТ”.pdf"), reply_markup=close_kb())
            await call.message.answer_document(InputFile("tg_bot/data/sertificates/ПИ к сертификату соответствия ХАЛЯЛЬ.pdf", "ПИ к сертификату соответствия “ХАЛЯЛЬ”.pdf"), reply_markup=close_kb())
            await call.message.answer_document(InputFile("tg_bot/data/sertificates/СЕРТИФИКАТ СООТВЕТСТВИЯ ВЫСШЕЕ КАЧЕСТВО БИО ПРОДУКТ.pdf", "СЕРТИФИКАТ СООТВЕТСТВИЯ “ВЫСШЕЕ КАЧЕСТВО” “БИО ПРОДУКТ”.pdf"), reply_markup=close_kb())
            await call.message.answer_document(InputFile("tg_bot/data/sertificates/СЕРТИФИКАТ СООТВЕТСТВИЯ ВЫСШЕЕ КАЧЕСТВО ХАЛЯЛЬ.pdf", "СЕРТИФИКАТ СООТВЕТСТВИЯ “ВЫСШЕЕ КАЧЕСТВО” “ХАЛЯЛЬ”.pdf"), reply_markup=close_kb())

        case _:
            await call.message.bot.send_chat_action(chat_id= call.message.chat.id, action= "upload_video")
            await call.message.answer_video(video = InputFile("вопросответ.mp4", filename = "Вопрос-ответ.mp4"), height=600, width=315, reply_markup= toabout_kb())


async def docs_actions(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    action = call.data.split("_")[1]
    match action:
        case "declaration":
            await call.message.answer_document(InputFile("tg_bot/data/sertificates/Декларация соответствия.pdf", "Декларация соответствия.pdf"), reply_markup=close_kb())
            await call.message.answer_document(InputFile("tg_bot/data/sertificates/ПИ к ДЕКЛАРАЦИИ.pdf", "Протокол контрольных испытаний к декларации.pdf"), reply_markup=close_kb())
        
        case "halal":
            await call.message.answer_document(InputFile("tg_bot/data/sertificates/СЕРТИФИКАТ СООТВЕТСТВИЯ ВЫСШЕЕ КАЧЕСТВО ХАЛЯЛЬ.pdf", "Сертификат ХАЛЯЛЬ.pdf"), reply_markup=close_kb())
            await call.message.answer_document(InputFile("tg_bot/data/sertificates/ПИ к сертификату соответствия ХАЛЯЛЬ.pdf", "Протокол контрольных испытаний ХАЛЯЛЬ.pdf"), reply_markup=close_kb())
        
        case "bio":
            await call.message.answer_document(InputFile("tg_bot/data/sertificates/СЕРТИФИКАТ СООТВЕТСТВИЯ ВЫСШЕЕ КАЧЕСТВО БИО ПРОДУКТ.pdf", "Сертификат БИО ПРОДУКТ.pdf"), reply_markup=close_kb())
            await call.message.answer_document(InputFile("tg_bot/data/sertificates/ПИ к сертификату соответствия БИО ПРОДУКТ.pdf", "Протокол контрольных испытаний БИО ПРОДУКТ.pdf"), reply_markup=close_kb())


async def payoff_application(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    balance = await get_referal_balance(call.from_user.id)
    if balance:
        await call.message.answer("✅ Ваша заявка на вывод успешно отправлена! Администраторы свяжутся с вами в ближайшее время для уточнения деталей", reply_markup= back_kb())
        await call.message.bot.send_message(chat_id= MAIN_REFERAL_ID, text = f"Появилась новая заявка на вывод от @{call.from_user.username}!\n\nСумма: <b>{balance}</b>") #TODO
    else:
        await call.message.answer("❌ Невозможно отправить заявку на вывод, так как ваш баланс реферального кабинета равен нулю!", reply_markup= back_kb())



async def process_catalog(message: types.Message, position: int):
    position = str(position)

    with open('tg_bot/description.json', 'r', encoding='utf-8') as file:
        text = json.load(file)[position]

    # Telegram ограничивает caption до 1024 символов, поэтому отправляем текст отдельным сообщением
    max_caption_length = 1024
    if len(text) > max_caption_length:
        # Отправляем фото без caption
        if message.caption:
            photo = InputFile(f"tg_bot/photos/{position}.png")
            await message.edit_media(media= InputMediaPhoto(media= photo), reply_markup= None)
        else:
            await message.delete()
            await message.answer_photo(photo = InputFile("tg_bot/photos/" + position + ".png"), reply_markup= None)
        # Отправляем текст отдельным сообщением с клавиатурой
        await message.answer(text, reply_markup= catalog_kb(position, position == "1", position == "7"))
    else:
        # Если текст короткий, отправляем с caption как раньше
        if message.caption:
            photo = InputFile(f"tg_bot/photos/{position}.png")
            await message.edit_media(media= InputMediaPhoto(media= photo, caption= text), reply_markup= catalog_kb(position, position == "1", position == "7"))
        else:
            await message.delete()
            await message.answer_photo(photo = InputFile("tg_bot/photos/" + position + ".png"), caption= text, reply_markup= catalog_kb(position, position == "1", position == "7"))



async def process_slide(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    _, pos, is_forward = call.data.split("_")
    pos = int(pos) 
    is_forward = bool(int(is_forward))
    pos = pos + 1 if is_forward else pos - 1
    pos = max(1, min(7, pos))  # каталог: позиции 1–7
    await process_catalog(call.message, pos)


async def process_add(call: types.CallbackQuery, state: FSMContext):
    pos = call.data.split("_")[1]
    await add_to_bucket(call.from_user.id, pos)
    await call.answer("✅ Позиция успешно добавлена в корзину!", show_alert=True)


async def proc_clear_bucket(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await clear_bucket(call.from_user.id)
    await call.message.edit_text("🗑️ Ваша корзина успешно очищена!", reply_markup= after_clear_kb())

async def start_pay(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    price = int(call.data.split("_")[1])
    if price:
        # TODO: добавить сбор адреса доставки через FSM
        adress = "Адрес будет уточнен после оплаты"
        pay_num = await create_pay(price, adress, call.from_user.username, call.from_user.id)
        payment_link = generate_payment_link(price, pay_num)
        
        payment_text = f"""✅ Для оформления заказа пептидов <b>BIO ACTIVE</b> Вам необходимо оплатить позиции, добавленные в корзину
Сумма к оплате: <u>{price}₽</u>

Платёж совершается в пользу:


<b>ООО "БИОАКТИВ.ПРО"
ИНН 9724222999 КПП 772401001
ОГРН 1257700282982
Юр. адрес: 115487, город Москва, ул. Академика Миллионщикова, д. 13 к. 1, помещ. 12е/п 
Р/СЧ 40702810802360006837
БАНК АО “АЛЬФА-БАНК”
КОР.СЧ 30101810200000000593
Контактный e-mail: info@bioactive.pro</b>"""
        
        await call.message.answer(payment_text, reply_markup=pay_kb(payment_link))


async def payed(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    price = int(call.data.split("_")[1])
    bucket_items_list, _, _ = await bucket_items(call.from_user.id)
    items = bucket_items_list.split("Сумма корзины")[0].split("Состав Вашей корзины 👇")[1]
    for admin_id in call.message.bot['config'].tg_bot.admin_ids:
        await call.message.bot.send_message(chat_id = int(admin_id), text = f"✅ Появился новый заказ!!!\nЗаказчик: <b>@{call.from_user.username}</b>\n💸 Сумма: <u>{price}₽</u>\n🛒 Состав заказа:{items}", reply_markup= contact_kb(call.from_user.username))
    
    await call.message.answer(f"✅ Заказ успешно оформлен!\n💸 Сумма заказа: <u>{price}₽</u>\n🛒 Состав заказа:{items}🤝 Наши сотрудники свяжутся с Вами как можно скорее для уточнения деталей!", reply_markup= back_kb())
    await clear_bucket(call.from_user.id)
    
    referal_ids, referal_texts = await process_referal_up(call.from_user.id, price)
    for i, referal_id in enumerate(referal_ids):
        if referal_id:
            await call.message.bot.send_message(chat_id= referal_id, text = referal_texts[i])
