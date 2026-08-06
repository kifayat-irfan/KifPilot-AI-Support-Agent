import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import get_settings

settings = get_settings()


class ChromaDBClient:
    def __init__(self):
        self._client: chromadb.ClientAPI | None = None

    def get_client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
        return self._client

    def get_or_create_collection(self, name: str, metadata: dict | None = None):
        client = self.get_client()
        return client.get_or_create_collection(name=name, metadata=metadata)

    def delete_collection(self, name: str) -> bool:
        client = self.get_client()
        try:
            client.delete_collection(name=name)
            return True
        except Exception:
            return False

    def reset(self) -> bool:
        client = self.get_client()
        try:
            client.reset()
            return True
        except Exception:
            return False


chroma_client = ChromaDBClient()