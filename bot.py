from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from tg_bot.config import load_config
from tg_bot.handlers import register_handlers, register_admin_handlers
from tg_bot.ai_assistent import RAGSystem
from tg_bot.DBSM import init_models
import asyncio, logging

storage = MemoryStorage()
logger = logging.getLogger(__name__)


def register_all_handlers(dp):
    register_admin_handlers(dp)
    register_handlers(dp)

async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
    )
    logger.info("Starting bot")
    
    # Инициализация таблиц БД
    logger.info("Initializing database tables...")
    await init_models()
    logger.info("Database tables initialized successfully")
    
    config = load_config('.env')
    bot = Bot(token=config.tg_bot.token, parse_mode = 'HTML')
    dp = Dispatcher(bot, storage=storage) 
    bot['config'] = config
    bot['rag_system'] = RAGSystem(fast_init= False, api_key = config.tg_bot.openai_api_key)
    register_all_handlers(dp)

    while True:
        try:
            await dp.start_polling()
        except Exception as e:
            if not isinstance(e, RuntimeError):
                print(e)


if __name__ == '__main__':
    asyncio.run(main())