from urllib import parse
from environs import Env
import hashlib, json, base64, aiohttp

env = Env()
env.read_env(".env")

# Определяем режим работы
TEST_MODE = env.str("TEST_MODE", "FALSE").upper() == "TRUE"

# Выбираем пароли в зависимости от режима
if TEST_MODE:
    password = env.str("ROBOKASSA_TEST_PASSWORD")
    password2 = env.str("ROBOKASSA_TEST_PASSWORD2")
else:
    password = env.str("ROBOKASSA_PASSWORD")
    password2 = env.str("ROBOKASSA_PASSWORD2")

login = env.str("ROBOKASSA_LOGIN")



def calculate_signature(*args) -> str:
    return hashlib.md5(':'.join(str(arg) for arg in args).encode()).hexdigest()

def generate_payment_json(cost):
    jsonn = {
        "sno":"osn",
        "items": [
            {
            "name": "Пополнение личного кабинета",
            "quantity": 1,
            "sum": cost,
            "payment_method": "full_prepayment",
            "payment_object": "service",
            "tax": "none"
            },
    ]}

    return parse.quote(json.dumps(jsonn))


# Формирование URL переадресации пользователя на оплату.
def generate_payment_link(
    cost:int,
    number: int,
) -> str:
    jsonn = {
        "sno":"usn_income_outcome",
        "items": [
            {
                "name": "Покупка пептидов",
                "quantity": 1,
                "sum": int(cost),
                "payment_method": "full_payment",
                "payment_object": "commodity",
                "tax": "none"
            },
        ]}
    jsonn = json.dumps(jsonn)
    
    json_decoded_first = parse.quote(jsonn)
            
    signature = calculate_signature(
        login,
        cost,
        number, 
        json_decoded_first,
        password
    )
    json_decoded_second = parse.quote(json_decoded_first)
    data = {
        'MerchantLogin': login,
        'OutSum': cost,
        'InvId': number,
        'Description': "Покупка пептидов",
        'SignatureValue': signature,
        'Receipt': json_decoded_second,
        'IsTest': 1 if TEST_MODE else 0
    }
    return f"{'https://auth.robokassa.ru/Merchant/Index.aspx'}?{parse.urlencode(data)}"