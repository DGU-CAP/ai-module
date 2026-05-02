import os
import chromadb
from openai import OpenAI
from app.core.config import settings


class Embedder:
    """
    FastAPI 시작 시 data/docs/*.md 문서를 읽어 ChromaDB에 임베딩하는 클래스.
    검색 시에도 동일한 임베딩 모델을 사용한다.
    """

    def __init__(self):
        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        self.chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self.collection = self.chroma_client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},  # 코사인 유사도 사용
        )

    def init_docs(self):
        """
        docs_dir의 마크다운 파일을 읽어 ChromaDB에 임베딩.
        이미 저장된 문서는 스킵한다 (중복 방지).
        """
        docs_dir = settings.docs_dir
        if not os.path.exists(docs_dir):
            print(f"[Embedder] docs 폴더 없음: {docs_dir}")
            return

        md_files = [f for f in os.listdir(docs_dir) if f.endswith(".md")]
        if not md_files:
            print("[Embedder] 임베딩할 문서 없음")
            return

        # 이미 저장된 doc_id 확인
        existing = set(self.collection.get()["ids"])

        new_docs = []
        for filename in md_files:
            doc_id = filename.replace(".md", "")
            if doc_id in existing:
                print(f"[Embedder] 스킵 (이미 존재): {filename}")
                continue

            filepath = os.path.join(docs_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            new_docs.append({"id": doc_id, "content": content, "filename": filename})

        if not new_docs:
            print("[Embedder] 모든 문서가 이미 임베딩됨")
            return

        # 배치로 임베딩
        contents = [d["content"] for d in new_docs]
        embeddings = self._embed_batch(contents)

        self.collection.add(
            ids=[d["id"] for d in new_docs],
            documents=contents,
            embeddings=embeddings,
            metadatas=[{"filename": d["filename"]} for d in new_docs],
        )
        print(f"[Embedder] {len(new_docs)}개 문서 임베딩 완료")

    def embed_query(self, query: str) -> list[float]:
        """검색 쿼리를 임베딩 벡터로 변환."""
        response = self.openai_client.embeddings.create(
            model=settings.openai_embedding_model,
            input=query,
        )
        return response.data[0].embedding

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """여러 텍스트를 한 번에 임베딩."""
        response = self.openai_client.embeddings.create(
            model=settings.openai_embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def search(self, query: str, top_k: int = None) -> list[str]:
        """
        쿼리와 유사한 문서를 ChromaDB에서 검색.

        Returns:
            유사 문서 내용 목록 (top_k개)
        """
        if top_k is None:
            top_k = settings.rag_top_k

        query_embedding = self.embed_query(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
        )

        # documents는 [[doc1, doc2, ...]] 형태로 반환됨
        if not results["documents"] or not results["documents"][0]:
            return []

        return results["documents"][0]


# 앱 전역에서 재사용할 싱글톤 인스턴스
# main.py lifespan에서 초기화됨
embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global embedder
    if embedder is None:
        raise RuntimeError("Embedder가 초기화되지 않았습니다. lifespan을 확인하세요.")
    return embedder


def init_embedder():
    global embedder
    embedder = Embedder()
    embedder.init_docs()