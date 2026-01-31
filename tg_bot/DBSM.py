from sqlalchemy import Column, Integer, Text, Boolean, select, BigInteger, DateTime, func, and_, JSON, text

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

# Список ID админов (уровень 1)
ADMIN_IDS = [int(x) for x in env.list("ADMIN_IDS", [])]

# Создание объекта Engine
engine = create_async_engine(DATABASE_URL, poolclass=NullPool)

# Создание базового класса для моделей
Base = declarative_base()


# Для обратной совместимости (первый админ = главный реферал)
MAIN_REFERAL_ID = ADMIN_IDS[0] if ADMIN_IDS else 0


positions = {
    "1": "BioActive соединительной ткани",
    "2": "BioActive яичников",
    "3": "BioActive эндометрия",
    "4": "BioActive for men I",
    "5": "BioActive for men II",
    "6": "BioActive щитовидной железы",
    "7": "BioActive для улучшения неврологического здоровья"
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
    referal_level = Column(Integer, default=0)  # 0 - обычный, 1 - MAIN, 2 - приглашён MAIN


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
    try:
        curr = await session.execute(select(User).filter(User.user_id == user_id))
        curr = curr.scalars().first()
        if curr:
            return False
        
        # Определяем уровень реферала:
        # - Админы (ADMIN_IDS) = уровень 1
        # - Приглашенные уровнем 1 = уровень 2
        # - Приглашенные уровнем 2 = уровень 0
        if user_id in ADMIN_IDS:
            level = 1
        else:
            # Проверяем уровень того, кто пригласил
            referal = await session.execute(select(User).filter(User.user_id == referal_id))
            referal = referal.scalars().first()
            
            if referal and referal.referal_level == 1:
                level = 2  # Приглашен админом -> уровень 2
            else:
                level = 0  # Приглашен рефералом 2 уровня или без реферала -> уровень 0

        now_date = datetime.now(pytz.timezone('Europe/Moscow'))
        new = User(
            username = username,
            user_id = user_id,
            date_register = now_date,
            referal = referal_id,
            referal_level = level
        )
        session.add(new)
        await session.commit()
        await session.refresh(new)
        return True
    finally:
        await session.close()


async def all_user():
    Session = async_sessionmaker()
    session = Session(bind = engine)
    all = await session.execute(select(User))
    all = all.scalars().all()
    await session.close()
    return all

async def is_invited(user_id):
    """
    Возвращает уровень реферала из БД:
    - 1: Админ (уровень первый)
    - 2: Приглашен админом (уровень второй)
    - 0: Обычный пользователь
    """
    Session = async_sessionmaker()
    session = Session(bind = engine)
    try:
        curr = await session.execute(select(User).filter(User.user_id == user_id))
        curr = curr.scalars().first()
        if not curr:
            return 0

        # Если уровень не установлен (исторические записи) — вычисляем и сохраняем
        if curr.referal_level is None or curr.referal_level == 0:
            if curr.user_id in ADMIN_IDS:
                new_level = 1
            else:
                # Проверяем уровень реферала
                if curr.referal:
                    referal = await session.execute(select(User).filter(User.user_id == curr.referal))
                    referal = referal.scalars().first()
                    if referal and referal.referal_level == 1:
                        new_level = 2
                    else:
                        new_level = 0
                else:
                    new_level = 0
            
            if new_level != 0:
                curr.referal_level = new_level
                await session.commit()

        return curr.referal_level or 0
    finally:
        await session.close()

async def get_referal_level(user_id):
    """
    Возвращает категорию реферала:
    - 'first': Админ (уровень 1)
    - 'second': Приглашен админом (уровень 2)
    - None: Обычный пользователь (уровень 0) - не видит рефералку
    """
    user_level = await is_invited(user_id)

    if user_level == 1:
        return 'first'   # Админ
    if user_level == 2:
        return 'second'  # Приглашён админом
    return None  # Обычный пользователь - не видит рефералку

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
        name = positions.get(key, f"Позиция №{key}")
        output += f"<u>Позиция №{key}</u>\nНазвание: <b>{name}</b>\nКоличество: <b>{value}</b>\n\n"

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
    """
    Реферальная система:
    Структура: Админ (ур.1) -> Реферал (ур.2) -> Покупатель (ур.0)
    
    - Если покупателя пригласил реферал уровня 2:
      - Реферал уровня 2 получает 40%
      - Админ (уровень 1) получает 10%
    - Если покупателя пригласил админ напрямую:
      - Админ получает 50%
    """
    first_text, second_text = None, None
    first_id, second_id = None, None

    Session = async_sessionmaker()
    session = Session(bind = engine)
    
    try:
        # Получаем покупателя
        buyer = await session.execute(select(User).filter(User.user_id == buyer_id))
        buyer = buyer.scalars().first()
        
        # Если у покупателя нет реферала - никому ничего не начисляем
        if not buyer or not buyer.referal:
            return (first_id, second_id), (first_text, second_text)
        
        # Получаем того, кто пригласил покупателя
        inviter_id = buyer.referal
        inviter = await session.execute(select(User).filter(User.user_id == inviter_id))
        inviter = inviter.scalars().first()
        
        if not inviter:
            return (first_id, second_id), (first_text, second_text)
        
        # Проверяем уровень пригласившего
        if inviter.referal_level == 2:
            # Покупателя пригласил реферал уровня 2 -> он получает 40%
            inviter.referal_balance = inviter.referal_balance + 0.4 * price
            first_text = f"🎉 Поздравляем! Ваш реферал совершил покупку на <u>{price}₽</u>\n💰 Баланс Вашего реферального кабинета пополнен на <u>{0.4*price}₽</u> (40%)"
            first_id = inviter_id
            
            # Админ (кто пригласил реферала уровня 2) получает 10%
            if inviter.referal:
                admin = await session.execute(select(User).filter(User.user_id == inviter.referal))
                admin = admin.scalars().first()
                if admin and admin.referal_level == 1:
                    admin.referal_balance = admin.referal_balance + 0.1 * price
                    second_text = f"🎉 Пользователь, приглашённый вашим рефералом, совершил покупку на <u>{price}₽</u>\n💰 Баланс пополнен на <u>{0.1*price}₽</u> (10%)"
                    second_id = inviter.referal
        
        elif inviter.referal_level == 1:
            # Покупателя пригласил админ напрямую -> админ получает 50%
            inviter.referal_balance = inviter.referal_balance + 0.5 * price
            first_text = f"🎉 Поздравляем! Ваш реферал совершил покупку на <u>{price}₽</u>\n💰 Баланс Вашего реферального кабинета пополнен на <u>{0.5*price}₽</u> (50%)"
            first_id = inviter_id
        
        await session.commit()
        return (first_id, second_id), (first_text, second_text)
    finally:
        await session.close()

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
    # Создаём таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Добавляем колонку referal_level если её нет (миграция для существующих БД)
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE "user" ADD COLUMN IF NOT EXISTS referal_level INTEGER DEFAULT 0
        """))
        
# asyncio.run(init_models())