from sqlalchemy import Column, Integer, Text, Boolean, select, BigInteger, DateTime, func, and_, JSON

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from environs import Env
from datetime import datetime, timedelta
import pytz, asyncio


env = Env()
env.read_env(".env")

# Получаем DATABASE_URL напрямую из .env
DATABASE_URL = env.str(
    "DATABASE_URL",
    default="postgresql+asyncpg://bioactive_user:bioactive_password@postgres:5432/bioactive_db"
)

# Создание объекта Engine
engine = create_async_engine(DATABASE_URL, poolclass=NullPool)

# Создание базового класса для моделей
Base = declarative_base()


MAIN_REFERAL_ID = 1007693291


positions = {
    "1": "BIOACTIVE яичников",
    "2": "BIOACTIVE эндометрия",
    "3": "BIOACTIVE для улучшения неврологического здоровья",
    "4": "BIOACTIVE для улучшения имунной системы",
    "5": "BIOACTIVE соединительной ткани", 
    "6": "BIOACTIVE for men"
}

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, autoincrement=True) #TODO
    username = Column(Text, nullable=True)
    user_id = Column(BigInteger)
    date_register = Column(DateTime(timezone=True))
    referal = Column(BigInteger, nullable=True)
    referal_balance = Column(Integer, default=0)
    bucket = Column(JSON, default= {})


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(Text, nullable= True)
    user_id = Column(BigInteger)
    cost = Column(Integer)
    pay_num = Column(BigInteger, unique = True)
    email = Column(Text, nullable=True)
    closed = Column(Boolean, nullable=True, default = False)
    date_close = Column(DateTime(timezone=True), nullable= True)
    adress = Column(Text)


# работа с пользователями
async def add_user(username, user_id, referal_id):
    Session = async_sessionmaker()
    session = Session(bind = engine)
    curr = await session.execute(select(User).filter(User.user_id == user_id))
    curr = curr.scalars().first()
    if curr:
        await session.close()
        return False
    
    now_date = datetime.now(pytz.timezone('Europe/Moscow'))
    new = User(username = username, user_id = user_id, date_register = now_date, referal = referal_id)
    session.add(new)
    await session.commit()
    await session.refresh(new)
    await session.close()
    return True


async def all_user():
    Session = async_sessionmaker()
    session = Session(bind = engine)
    all = await session.execute(select(User))
    all = all.scalars().all()
    await session.close()
    return all

async def is_invited(user_id):
    Session = async_sessionmaker()
    session = Session(bind = engine)
    curr = await session.execute(select(User).filter(User.user_id == user_id))
    curr = curr.scalars().first()
    await session.close()
    if curr.user_id == MAIN_REFERAL_ID:
        return 2
    elif curr.referal == MAIN_REFERAL_ID:
        return 1
    else:
        return 0

async def get_referals_count(user_id):
    Session = async_sessionmaker()
    session = Session(bind = engine)
    result = await session.execute(select(func.count(User.id)).filter(User.referal == user_id))
    await session.close()
    return result.scalar()

async def get_referal_balance(user_id):
    Session = async_sessionmaker()
    session = Session(bind = engine)
    curr = await session.execute(select(User).filter(User.user_id == user_id))
    curr = curr.scalars().first()   
    await session.close()
    return f"{curr.referal_balance}₽"

async def get_ref_balance_by_username(username):
    Session = async_sessionmaker()
    session = Session(bind = engine)
    curr = await session.execute(select(User).filter(User.username == username))
    curr = curr.scalars().first()  
    if not curr:
        await session.close()
        return "❌ Пользователь с таким юзернеймом не найден" 
    
    await session.close()
    return f"Баланс реферального кабинета пользователя @{username} составляет <u>{curr.referal_balance}₽</u>"


#работа с корзиной
async def add_to_bucket(user_id, pos):
    Session = async_sessionmaker()
    session = Session(bind = engine)
    curr = await session.execute(select(User).filter(User.user_id == user_id))
    curr = curr.scalars().first()  
    bucket_data = curr.bucket.copy()

    if pos in bucket_data:
        bucket_data[pos] = bucket_data[pos] + 1
    else:
        bucket_data[pos] = 1

    curr.bucket = bucket_data
    await session.commit()
    await session.close()

async def remove_from_bucket(user_id, pos):
    Session = async_sessionmaker()
    session = Session(bind = engine)
    curr = await session.execute(select(User).filter(User.user_id == user_id))
    curr = curr.scalars().first() 
    bucket = curr.bucket
    del bucket[pos]
    curr.bucket = bucket

    await session.commit()
    await session.close()

async def clear_bucket(user_id):
    Session = async_sessionmaker()
    session = Session(bind = engine)
    curr = await session.execute(select(User).filter(User.user_id == user_id))
    curr = curr.scalars().first() 
    curr.bucket = {}
    await session.commit()
    await session.close()

async def bucket_items(user_id):
    output = "Состав Вашей корзины 👇\n\n"
    Session = async_sessionmaker()
    session = Session(bind = engine)
    curr = await session.execute(select(User).filter(User.user_id == user_id))
    curr = curr.scalars().first() 
    bucket = curr.bucket
    for key, value in bucket.items():
        output += f"<u>Позиция №{key}</u>\nНазвание: <b>{positions[key]}</b>\nКоличество: <b>{value}</b>\n\n"

    items_count = sum(int(value) for value in bucket.values())
    if items_count < 3:
        sum_bucket, price = f"Сумма корзины составляет <b>{items_count * 4700}₽</b>", items_count * 4700
    elif 3 <= items_count < 6:
        sum_bucket, price = f"Сумма корзины составляет <b>{13500 + 4700 * (items_count - 3)}₽</b>", 13500 + 4700 * (items_count - 3)
    elif items_count == 6:
        sum_bucket, price = "Сумма корзины составляет <b>24.000₽</b>\nP.S. <i>При заказе 6 флаконов 7-й идёт в подарок, так что Вы можете добавить его в корзину и получить абсолютно бесплатно!</i>", 24000
    elif items_count == 7:
        sum_bucket, price = "Сумма корзины составляет <b>24.000₽</b>\nP.S. <i>При заказе 6 флаконов 7-й идёт в подарок, так что Вы получаете один флакон пептидов <b>BIO ACTIVE</b> абсолютно бесплатно!</i>", 24000
    elif items_count > 7:
        sum_bucket, price = f"Сумма корзины составляет <b>{24000 + 4700 * (items_count - 7)}₽</b>\nP.S. <i>При заказе 6 флаконов 7-й идёт в подарок, так что Вы получаете один флакон пептидов <b>BIO ACTIVE</b> абсолютно бесплатно!</i>", 24000 + 4700 * (items_count - 7)
    
    output += sum_bucket
    if not bucket:
        output = "😢 К сожалению, в Вашей корзине не находится ни одного товара"

    await session.close()
    return output, price, not bucket



# работа с рефералами
async def process_referal_up(buyer_id, price):
    tatiana_text, first_text, second_text = None, None, None
    tatiana_id, first_id, second_id = None, None, None

    Session = async_sessionmaker()
    session = Session(bind = engine)
    curr = await session.execute(select(User).filter(User.user_id == buyer_id))
    curr = curr.scalars().first()

    if curr.user_id == MAIN_REFERAL_ID : 
        pass

    else:
        tatiana_text = f"🎉 Поздравляем, пользователь бота совершил покупку на <u>{price}₽</u>, баланс Вашего реферального кабинета пополнен на <u>{0.05*price}₽</u>, как главного партнёра"
        tatiana_id = MAIN_REFERAL_ID


        first_referal_id = curr.referal
        first_referal = await session.execute(select(User).filter(User.user_id == first_referal_id))
        first_referal = first_referal.scalars().first()
        
        if first_referal.referal != MAIN_REFERAL_ID and first_referal.user_id != MAIN_REFERAL_ID:
            second_referal_id = first_referal.referal
            second_referal = await session.execute(select(User).filter(User.user_id == second_referal_id))
            second_referal = second_referal.scalars().first()
            first_referal.referal_balance = first_referal.referal_balance + 0.15*price
            second_referal.referal_balance = second_referal.referal_balance + 0.05*price

            first_text = f"🎉 Поздравляем, Ваш реферал совершил покупку на <u>{price}₽</u>, баланс Вашего реферального кабинета пополнен на <u>{0.15*price}₽</u>"
            second_text =  f"🎉 Поздравляем, пользователь, приглашённый Вашим рефералом, совершил покупку на <u>{price}₽</u>, баланс Вашего реферального кабинета пополнен на <u>{0.05*price}₽</u>"
            first_id = first_referal_id
            second_id = second_referal_id

        else: 
            first_referal.referal_balance = first_referal.referal_balance + 0.2*price
            
            first_text = f"🎉 Поздравляем, Ваш реферал совершил покупку на <u>{price}₽</u>, баланс Вашего реферального кабинета пополнен на <u>{0.2*price}₽</u>"
            first_id = first_referal_id
    
    await session.commit()
    await session.close()
    return (tatiana_id, first_id, second_id), (tatiana_text, first_text, second_text)

async def process_referal_table():
    Session = async_sessionmaker()
    session = Session(bind = engine)
    all = await session.execute(select(User))
    all = all.scalars().all()
    await session.close()
    return all




#работа с платежами
async def create_pay(cost, adress, username, user_id):
    Session = async_sessionmaker()
    session = Session(bind=engine)

    # Получение максимального номера платежа
    max_id_query = select(func.max(Payment.pay_num))
    max_id_result = await session.execute(max_id_query)
    max_id = max_id_result.scalar()
    
    new_num = max_id + 1 if max_id else 1

    # Создание нового платежа
    new = Payment(username=username, cost=cost, pay_num=new_num, user_id=user_id, adress=adress)
    
    session.add(new)
    await session.commit()
    await session.refresh(new)
    await session.close()
    
    return new_num


async def pay_data(number):
    Session = async_sessionmaker()
    session = Session(bind = engine)
    curr = await session.execute(select(Payment).filter(Payment.pay_num == number))
    curr = curr.scalar_one_or_none()
    await session.close()
    return curr.username, curr.user_id, curr.cost, curr.adress


async def close_payment(number, outsum):
    Session = async_sessionmaker()
    session = Session(bind = engine)
    curr = await session.execute(select(Payment).filter(Payment.pay_num == number))
    curr = curr.scalar_one_or_none()
    curr.closed = True
    curr.date_close = datetime.now(pytz.timezone('Europe/Moscow'))
    await session.commit()
    await session.close()


async def is_closed(number):
    Session = async_sessionmaker()
    session = Session(bind = engine)
    curr = await session.execute(select(Payment).filter(Payment.pay_num == number))
    curr = curr.scalar_one_or_none()
    await session.close()
    return curr.closed


    



    









# работа со статистикой
class Stats:
    def __init__(self):
        self.now = datetime.now(pytz.timezone("Europe/Moscow"))
    
    async def get_today_registrations(self):
        today_start = self.now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        query = select(func.count(User.id)).where(
            and_(
                User.date_register >= today_start,
                User.date_register < today_end
            )
        )
        Session = async_sessionmaker()
        session = Session(bind = engine)
        result = await session.execute(query)
        await session.close()
        return result.scalar()
    
    async def get_this_week_registrations(self):
        days_since_monday = self.now.weekday()
        week_start = (self.now - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        week_end = week_start + timedelta(days=7)
        
        query = select(func.count(User.id)).where(
            and_(
                User.date_register >= week_start,
                User.date_register < week_end
            )
        )
        Session = async_sessionmaker()
        session = Session(bind = engine)
        result = await session.execute(query)
        await session.close()
        return result.scalar()
    
    async def get_this_month_registrations(self):
        month_start = self.now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if self.now.month == 12:
            next_month_start = month_start.replace(year=self.now.year + 1, month=1)
        else:
            next_month_start = month_start.replace(month=self.now.month + 1)
        
        query = select(func.count(User.id)).where(
            and_(
                User.date_register >= month_start,
                User.date_register < next_month_start
            )
        )
        Session = async_sessionmaker()
        session = Session(bind = engine)
        result = await session.execute(query)
        await session.close()
        return result.scalar()
    
    async def get_all_user(self):
        Session = async_sessionmaker()
        session = Session(bind = engine)
        all = await session.execute(select(func.count(User.id)))
        await session.close()
        return all.scalar()  
      
    async def get_ref_user(self):
        Session = async_sessionmaker()
        session = Session(bind = engine)
        all = await session.execute(select(func.count(User.id)).filter(User.referal.is_not(None)))
        await session.close()
        return all.scalar()    

    async def get_all_stats(self):
        return {
            'all': await self.get_all_user(),
            'all_ref': await self.get_ref_user(),
            'today': await self.get_today_registrations(),
            'week': await self.get_this_week_registrations(),
            'month': await self.get_this_month_registrations()
        }




async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
# asyncio.run(init_models())