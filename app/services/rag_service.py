from typing import List
from app.core.config import settings


def search(query: str, top_k: int = 3) -> List[str]:
    """Vector DB에서 유사 장애 사례를 검색한다."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)
        collection = client.get_or_create_collection("incident_cases")

        if collection.count() == 0:
            return []

        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()),
        )
        documents = results.get("documents", [[]])[0]
        return documents

    except Exception:
        return []


def add_documents(documents: List[str], ids: List[str]) -> None:
    """장애 문서를 Vector DB에 추가한다."""
    import chromadb
    client = chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)
    collection = client.get_or_create_collection("incident_cases")
    collection.add(documents=documents, ids=ids)
