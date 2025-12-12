import os
import glob
import time
from typing import List, Dict, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from openai import AsyncOpenAI
import logging
import httpx



# Конфигурация
OPENAI_MODEL = "gpt-4o-2024-08-06"  
OPENAI_EMBEDDING_MODEL = "text-embedding-ada-002"  
CHUNK_SIZE = 1000  # Размер чанка для разбиения документов
CHUNK_OVERLAP = 200  # Перекрытие между чанками
PDF_DIRECTORY = "tg_bot/ai_files"  # Директория с PDF-файлами
VECTOR_DB_PATH = "vector_db"  # Путь для хранения векторной базы данных
SHOW_CONTEXT_PREVIEW = False  # Показывать предпросмотр контекста в консоли

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("rag_telegram_bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Таймауты для HTTP-запросов
CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 15.0
TOTAL_TIMEOUT = 30.0

# Максимальное количество попыток подключения
MAX_RETRIES = 1

MAX_BATCH_SIZE = 200




class RAGSystem:
    def __init__(self, fast_init=False, api_key=None):
        """Инициализация системы RAG
        
        Args:
            fast_init (bool): Если True, использует ускоренную инициализацию с ограничением количества документов
            api_key (str, optional): API ключ OpenAI, если отличается от глобального
        """
        logger.info("Инициализация системы RAG")
        self.fast_init = fast_init
        self.api_key = api_key

        self._setup_openai_client()
        self._setup_vector_stores()
    
    def _setup_openai_client(self):
        """Настройка OpenAI клиента для генерации ответов"""
        try:
            self.client_http = httpx.AsyncClient(proxy="http://5DqVFTWh:VAHjRyn1@142.252.43.239:64250")
            logger.info(f"Настроен HTTP клиент с таймаутами")
        except Exception as e:
            logger.error(f"Ошибка при настройке HTTP клиента: {e}", exc_info=True)
            # Создаем клиент с базовыми настройками в случае ошибки
            self.client_http = httpx.AsyncClient(proxy="http://5DqVFTWh:VAHjRyn1@142.252.43.239:64250", timeout= 60.0)
        
        try:
            # Создаем клиент OpenAI
            self.client = AsyncOpenAI(api_key=self.api_key, http_client=self.client_http)
            logger.info("Успешно создан клиент OpenAI")
        except Exception as e:
            logger.error(f"Ошибка при создании клиента OpenAI: {e}", exc_info=True)
            self.client = None

    
    
    def _setup_vector_stores(self):
        try:
            # Настройка OpenAIEmbeddings с таймаутом
            embedding_kwargs = {
                "openai_api_key": self.api_key,
                "model": OPENAI_EMBEDDING_MODEL,  # Используем модель для эмбеддингов
                "request_timeout": TOTAL_TIMEOUT,
                "http_client": httpx.Client(proxy="http://5DqVFTWh:VAHjRyn1@142.252.43.239:64250")
            }
            
            self.embeddings = OpenAIEmbeddings(**embedding_kwargs)
            logger.info("Успешно создан объект OpenAIEmbeddings")
        except Exception as e:
            logger.error(f"Ошибка при создании OpenAIEmbeddings: {e}", exc_info=True)
            raise
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len
        )
        
        logger.info("Запуск загрузки векторных хранилищ")
        
        # Инициализируем хранилище
        self._load_or_create_vector_store()
        logger.info("Инициализация RAG завершена")
    
    def _load_or_create_vector_store(self):
        """Загрузка существующего векторного хранилища или создание нового"""
        os.makedirs(VECTOR_DB_PATH, exist_ok=True)
        os.makedirs(PDF_DIRECTORY, exist_ok=True)
        
        vector_store_path = os.path.join(VECTOR_DB_PATH, "pdf_faiss")
        
        try:
            if os.path.exists(vector_store_path):
                # Пытаемся загрузить существующее хранилище
                try:
                    self.vector_store = FAISS.load_local(
                        vector_store_path, 
                        self.embeddings,
                        allow_dangerous_deserialization=True
                    )
                    logger.info("Загружено существующее векторное хранилище")
                    return
                except Exception as e:
                    logger.error(f"Ошибка загрузки векторного хранилища: {e}")
                    # Если не удалось загрузить, создаем новое
            
            # Создание нового хранилища
            self._create_vector_store(vector_store_path)
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации хранилища: {e}")
            raise
    
    def _process_chunks_in_batches(self, text_chunks):
        """Обработка чанков порциями для обхода ограничений OpenAI на количество токенов"""
        logger.info(f"Обработка {len(text_chunks)} чанков порциями по {MAX_BATCH_SIZE}")
        
        # Разделяем чанки на батчи
        batches = [text_chunks[i:i + MAX_BATCH_SIZE] for i in range(0, len(text_chunks), MAX_BATCH_SIZE)]
        
        # Создаем начальное хранилище с первым батчем
        logger.info(f"Создание начального хранилища с первым батчем из {len(batches[0])} чанков")
        
        vector_store = FAISS.from_documents(batches[0], self.embeddings)
        
        # Обрабатываем остальные батчи
        if len(batches) > 1:
            logger.info(f"Обработка оставшихся {len(batches)-1} батчей")
            
            for i, batch in enumerate(batches[1:]):
                try:
                    # Создаем временное хранилище для текущего батча
                    temp_store = FAISS.from_documents(batch, self.embeddings)
                    
                    # Объединяем с основным хранилищем
                    vector_store.merge_from(temp_store)
                    
                    logger.info(f"Обработан батч {i+2}/{len(batches)}")
                    
                    # Добавляем небольшую паузу для стабильности API
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Ошибка при обработке батча {i+2}: {e}")
                    # Продолжаем с следующим батчем
        
        return vector_store
    
    def _create_vector_store(self, vector_store_path):
        """Создание векторного хранилища из PDF файлов"""
        try:
            documents = []
            
            # Проверяем наличие PDF файлов
            pdf_files = glob.glob(os.path.join(PDF_DIRECTORY, "**/*.pdf"), recursive=True)
            
            if not pdf_files:
                logger.warning(f"В директории {PDF_DIRECTORY} не найдено PDF файлов")
                # Создаем пустое хранилище
                self.vector_store = FAISS.from_documents(
                    [Document(page_content="Пустое хранилище", metadata={"source": "init"})],
                    self.embeddings
                )
                self.vector_store.save_local(vector_store_path)
                return
            
            logger.info(f"Найдено {len(pdf_files)} PDF файлов")
            
            # Ограничиваем количество файлов при быстрой инициализации
            if self.fast_init and len(pdf_files) > 2:
                logger.info(f"Быстрая инициализация: ограничение до 2 PDF файлов")
                pdf_files = pdf_files[:2]
            
            # Загрузка каждого PDF файла
            for pdf_file in pdf_files:
                try:
                    logger.info(f"Загрузка файла: {pdf_file}")
                    
                    loader = PyPDFLoader(pdf_file)
                    pdf_documents = loader.load()
                    
                    # Ограничение для быстрой инициализации
                    if self.fast_init and len(pdf_documents) > 5:
                        logger.info(f"Быстрая инициализация: ограничение до 5 страниц для {pdf_file}")
                        pdf_documents = pdf_documents[:5]
                    
                    documents.extend(pdf_documents)
                    logger.info(f"Загружен PDF файл: {pdf_file} ({len(pdf_documents)} страниц)")
                except Exception as e:
                    logger.error(f"Ошибка при загрузке файла {pdf_file}: {e}")
            
            if not documents:
                logger.warning("Не удалось загрузить ни одного документа")
                # Создаем пустое хранилище
                self.vector_store = FAISS.from_documents(
                    [Document(page_content="Пустое хранилище", metadata={"source": "init"})],
                    self.embeddings
                )
                self.vector_store.save_local(vector_store_path)
                return
            
            # Разбиение документов на чанки
            logger.info(f"Разбиение {len(documents)} документов на чанки")
            text_chunks = self.text_splitter.split_documents(documents)
            
            # Создание векторного хранилища батчами
            logger.info(f"Создание векторного хранилища из {len(text_chunks)} чанков")
            
            # Обрабатываем чанки порциями
            self.vector_store = self._process_chunks_in_batches(text_chunks)
            
            # Сохранение хранилища
            logger.info(f"Сохранение векторного хранилища в {vector_store_path}")
            self.vector_store.save_local(vector_store_path)
            
            logger.info("Векторное хранилище успешно создано и сохранено")
            
        except Exception as e:
            logger.error(f"Ошибка при создании векторного хранилища: {e}")
            raise
    
    def retrieve_relevant_context(self, query: str, top_k: int = 5) -> Tuple[List[str], List[Dict]]:
        """Получение релевантного контекста для запроса"""
        try:
            if not hasattr(self, 'vector_store'):
                logger.warning("Векторное хранилище не инициализировано")
                return [], []
            
            # Поиск релевантных документов
            docs_with_scores = self.vector_store.similarity_search_with_score(query, k=top_k)
            
            contexts = []
            metadata_list = []
            
            for doc, score in docs_with_scores:
                # Пропускаем начальный документ
                if doc.metadata.get('source') == 'init':
                    continue
                    
                contexts.append(doc.page_content)
                metadata_list.append({
                    "source": doc.metadata.get("source", ""),
                    "score": float(score),
                    "page": doc.metadata.get("page", "")
                })
            
            return contexts, metadata_list
        except Exception as e:
            logger.error(f"Ошибка при поиске контекста: {e}")
            return [], []
    
    async def generate_response(self, query: str) -> Tuple[str, bool]:
        """Генерация ответа с использованием RAG"""
        try:
            logger.info(f"Поиск контекста для запроса: '{query}'")
            
            contexts, metadata_list = self.retrieve_relevant_context(query, top_k=5)
            
            # Проверяем наличие контекста
            if not contexts:
                logger.info("Релевантный контекст не найден, генерация ответа без контекста")
                response = self._query_openai(query, [])
                return response, False
            
            logger.info(f"Найдено {len(contexts)} контекстов, генерация ответа")
            
            # Выводим найденный контекст только в логи
            for i, (context, meta) in enumerate(zip(contexts, metadata_list)):
                source = meta.get("source", "")
                if source and os.path.exists(source):
                    source = os.path.basename(source)
                score = meta.get("score", 0)
                page = meta.get("page", "")
                
                logger.info(f"Источник {i+1}: {source} (стр. {page}, релевантность: {score:.2f})")
            
            # Генерируем ответ от OpenAI с учетом контекста
            final_response = await self._query_openai(query, contexts)
            
            
            return final_response, True
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}", exc_info=True)
            return f"Произошла ошибка при генерации ответа: {str(e)}", False
    
    async def _query_openai(self, query: str, contexts: List[str]) -> str:
        """Отправка запроса к OpenAI API"""
        try:
            # Если клиент не был инициализирован, пробуем создать его
            if self.client is None:
                logger.info("Попытка создания OpenAI клиента по требованию")
                self._setup_openai_client()
                if self.client is None:
                    raise ValueError("Не удалось создать OpenAI клиент")
            
            system_message = (
                "Ты ассистент онлайн-магазина пептидов (БАД) BIO ACTIVE "
                "Пептиды BIO ACTIVE можно приобрести в Telegram-боте @bioactive_bot, а также на официальном сайте магазина bioactive.pro "
                "Твоя главная задача - консультировать покупателей по пептидам, предлагать, какой тип пептидов лучше всего им подойдёт и т.д. В общем, отвечать на все интересующие клиента вопросы "
                "Тебе нужно отвечать на основе предоставленной информации. Если информация будет не найдена, ответь 'К сожалению, не нашё информацию по Вашему запросу, можете задать мне другой вопрос или для уточнения деталей связаться с Администратором' "
                "Твой стиль общения должен быть профессиональный, общайся с клиентом как настоящий менеджер, отвечай только по сути вопроса и консультируй так, чтобы клиент купил пептиды. Слово Вы и любые другие его формы, включая притяжательные, пиши всегда с большой буквы"
            )
            
            if contexts:
                print(contexts)
                # Форматируем контексты
                formatted_contexts = []
                for i, ctx in enumerate(contexts):
                    formatted_context = f"[Документ {i+1}]\n{ctx}"
                    formatted_contexts.append(formatted_context)
                    
                # Объединяем контексты
                total_context = "\n\n".join(formatted_contexts)
                system_message += "\n\nИспользуй следующую информацию для ответа:\n" + total_context
                print(system_message)
            else:
                system_message += "\n\nИнформация не найдена"
            
            logger.info(f"Отправка запроса в OpenAI, длина системного сообщения: {len(system_message)}")
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": query}
            ]
            
            # Используем стандартный вызов API
            response = await self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.3,
                n=1,
                timeout=30
            )
            
            logger.info("Получен ответ от OpenAI API")
            
            reply = response.choices[0].message.content.strip()
            
            # Если ответ был сгенерирован без контекста, добавляем уведомление
            if not contexts:
                logger.info("Ответ сгенерирован без найденного контекста")
                reply += "\n\n(В документах не найдена информация по вашему запросу)"
            
            # Логируем ответ от OpenAI
            logger.info(f"Ответ от OpenAI:\n{reply}")
            
            return reply
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Ошибка при запросе к OpenAI: {error_message}")
            # Более подробное логирование ошибки
            logger.error(f"Детали ошибки OpenAI: {type(e).__name__} - {error_message}")
            return f"Произошла ошибка при запросе к API OpenAI: {error_message}"
    



