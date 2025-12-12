from flask import Flask, redirect, request
from aiogram import Bot
from environs import Env

from tg_bot.DBSM import pay_data, is_closed, close_payment, bucket_items, process_referal_up, clear_bucket
from tg_bot.robokassa import calculate_signature
from tg_bot.keyboards import back_kb, contact_kb

import urllib, urllib.parse

env = Env()
env.read_env(".env")
app = Flask(__name__)


@app.route("/payment/result", methods = ["POST", "GET"])
async def result():
    if request.method == "POST":
        bot = Bot(token= env.str("BOT_TOKEN"), parse_mode= "HTML")
        raw_data = request.get_data()
        data_str = raw_data.decode('utf-8')
        data_dict = urllib.parse.parse_qs(data_str)
        clean_data_dict = {k: v[0] for k, v in data_dict.items()}
        recieved_signature = clean_data_dict['SignatureValue']
        outsum = int(clean_data_dict['OutSum'].split(".")[0])
        paynum = int(clean_data_dict["InvId"])


        if recieved_signature != calculate_signature(clean_data_dict['OutSum'], clean_data_dict["InvId"], env.str("ROBOKASSA_PASSWORD2")).upper():
            return redirect("https://t.me/bioactive_bot")

        if await is_closed(paynum):
            return redirect("https://t.me/bioactive_bot")
        
        await close_payment(paynum, outsum)
        username, user_id, cost, adress = await pay_data(paynum)
        bucket_items_list, _, _ = await bucket_items(user_id)
        items = bucket_items_list.split("Сумма корзины")[0].split("Состав Вашей корзины 👇")[1]
        admin_ids = env.list("ADMIN_IDS")
        for admin_id in admin_ids:
            await bot.send_message(chat_id = int(admin_id), text = f"✅ Появился новый заказ!!!\nЗаказчик: <b>@{username}</b>\n💸 Сумма: <u>{cost}₽</u>\n🛒 Состав заказа:{items}\n📍 Адрес: <code>{adress}</code>", reply_markup= contact_kb(username))
        
        await bot.send_message(chat_id= user_id, text = f"✅ Заказ успешно оформлен!\n💸 Сумма заказа: <u>{cost}₽</u>\n🛒 Состав заказа:{items}🤝 Наши сотрудники свяжутся с Вами как можно скорее для уточнения деталей!", reply_markup= back_kb())
        await clear_bucket(user_id)
        
        referal_ids, referal_texts = await process_referal_up(user_id, cost)
        for i, referal_id in enumerate(referal_ids):
            if referal_id:
                await bot.send_message(chat_id= referal_id, text = referal_texts[i]) 

    return redirect("https://t.me/bioactive_bot")


@app.route("/payment/sucess", methods = ["POST", "GET"])
async def sucess():
    return redirect("https://t.me/bioactive_bot")


@app.route("/payment/unsucess", methods = ["POST", "GET"])
async def unsucess():
    return redirect("https://t.me/bioactive_bot")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
