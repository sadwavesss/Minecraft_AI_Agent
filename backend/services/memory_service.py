import os
import time

import chromadb
from chromadb.utils import embedding_functions

from backend.core.config import settings

# Максимальное количество сообщений, хранимых в ChromaDB.
# Предотвращает раздувание промпта при длинных сессиях (Truncation по ТЗ).
_MAX_COLLECTION_SIZE = 100


class MemoryService:
    """
    Сервис долговременной памяти на базе ChromaDB.
    Хранит историю диалога и реализует RAG для контекстного поиска.
    """

    def __init__(self):
        import threading
        db_path = os.path.join(os.getcwd(), "data", "chroma")
        os.makedirs(db_path, exist_ok=True)

        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = None
        self.model_loaded = False

        # Загружаем модель последовательно
        self._init_memory()

    def _init_memory(self):
        # Локальные эмбеддинги (Sentence-Transformers) — без отправки данных на внешние серверы
        try:
            print("[INFO] Инициализация модели эмбеддингов (all-MiniLM-L6-v2)...")
            embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            try:
                self.collection = self.client.get_or_create_collection(
                    name="dialogue_history",
                    embedding_function=embedding_fn,
                    metadata={"hnsw:space": "cosine"},
                )
                self.model_loaded = True
                print("[SUCCESS] Память (ChromaDB) успешно инициализирована.")
                
                # Эффективная очистка коллекции без удаления самой коллекции (быстрее)
                count = self.collection.count()
                if count > 0:
                    all_ids = self.collection.get(include=[])["ids"]
                    self.collection.delete(ids=all_ids)
                print("[INFO] Память автоматически очищена при запуске.")
            except Exception as coll_err:
                # Если возникает конфликт функций эмбеддингов (была создана с дефолтной, а теперь другая)
                if "Embedding function conflict" in str(coll_err):
                    print("[WARNING] ChromaDB Embedding conflict detected. Удаляем старую коллекцию и пересоздаем...")
                    try:
                        self.client.delete_collection("dialogue_history")
                    except Exception:
                        pass
                    
                    self.collection = self.client.get_or_create_collection(
                        name="dialogue_history",
                        embedding_function=embedding_fn,
                        metadata={"hnsw:space": "cosine"},
                    )
                    self.model_loaded = True
                    print("[SUCCESS] Память (ChromaDB) пересоздана.")
                else:
                    raise coll_err
                
        except Exception as e:
            print(f"[ERROR] Не удалось загрузить модель эмбеддингов ChromaDB: {e}")
            print("[WARNING] Память будет работать в ограниченном режиме.")
            # Попытка создать коллекцию без функции (для базовых операций)
            try:
                self.collection = self.client.get_or_create_collection(
                    name="dialogue_history",
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception:
                pass

    def add_message(self, role: str, content: str) -> None:
        """Добавляет сообщение в историю. При превышении лимита удаляет старейшие записи."""
        if self.collection is None:
            return

        self._truncate_if_needed()

        msg_id = f"{role}_{time.time()}"
        try:
            self.collection.add(
                ids=[msg_id],
                documents=[content],
                metadatas=[{"role": role, "timestamp": time.time()}],
            )
        except Exception as e:
            print(f"[ERROR] Failed to add message to memory: {e}")

    def get_context(self, query: str, n_results: int = 5) -> str:
        """Возвращает семантически близкие фрагменты из истории диалога."""
        if self.collection is None:
            return ""

        # ChromaDB выбрасывает исключение, если коллекция пуста или n_results > кол-во записей
        count = self.collection.count()
        if count == 0:
            return ""

        actual_n = min(n_results, count)
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=actual_n,
            )
            if results and results["documents"]:
                return "\n".join(results["documents"][0])
        except Exception as e:
            print(f"[ERROR] Memory query failed: {e}")

        return ""

    def get_recent_history(self, limit: int = 10) -> list:
        """Возвращает последние N сообщений в хронологическом порядке."""
        if self.collection is None:
            return []

        count = self.collection.count()
        if count == 0:
            return []
        
        # Получаем все сообщения, сортируем по времени и берем последние
        all_data = self.collection.get(include=["metadatas", "documents"])
        items = []
        for i in range(len(all_data["ids"])):
            items.append({
                "role": all_data["metadatas"][i]["role"],
                "content": all_data["documents"][i],
                "timestamp": all_data["metadatas"][i]["timestamp"]
            })
        
        # Сортировка по времени (от старых к новым)
        sorted_items = sorted(items, key=lambda x: x["timestamp"])
        return sorted_items[-limit:]

    def clear_session(self) -> None:
        """Полностью очищает историю диалога без удаления коллекции."""
        if self.collection:
            try:
                count = self.collection.count()
                if count > 0:
                    all_ids = self.collection.get(include=[])["ids"]
                    self.collection.delete(ids=all_ids)
                print("[INFO] Memory cleared.")
            except Exception as e:
                print(f"[ERROR] Не удалось очистить ChromaDB: {e}")

    def _truncate_if_needed(self) -> None:
        """Удаляет самые старые записи, если превышен лимит _MAX_COLLECTION_SIZE."""
        if self.collection is None:
            return

        count = self.collection.count()
        if count < _MAX_COLLECTION_SIZE:
            return

        # Получаем все записи с метаданными, сортируем по timestamp, удаляем старейшие
        overflow = count - _MAX_COLLECTION_SIZE + 1
        all_items = self.collection.get(include=["metadatas"])
        if not all_items or not all_items["ids"]:
            return

        # Сортируем по timestamp и берём самые старые
        items_with_ts = sorted(
            zip(all_items["ids"], all_items["metadatas"]),
            key=lambda x: x[1].get("timestamp", 0),
        )
        ids_to_delete = [item_id for item_id, _ in items_with_ts[:overflow]]
        self.collection.delete(ids=ids_to_delete)
