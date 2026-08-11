from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient

from cv_agent.config import Settings
from cv_agent.knowledge.loader import load_knowledge
from cv_agent.retrieval.azure_search import AzureSearchRetrieval
from cv_agent.retrieval.base import RetrievalService
from cv_agent.retrieval.embeddings import OpenAIEmbeddingProvider
from cv_agent.retrieval.service import HybridCvRetrieval


def build_retrieval(
    settings: Settings,
    knowledge_directory: Path,
) -> RetrievalService:
    if settings.environment != "production":
        return HybridCvRetrieval.from_directory(knowledge_directory)
    if not settings.azure_search_endpoint:
        raise RuntimeError(
            "AZURE_SEARCH_ENDPOINT es obligatorio en producción"
        )
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY es obligatorio en producción"
        )
    credential = DefaultAzureCredential()
    client = SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_index,
        credential=credential,
    )
    embeddings = OpenAIEmbeddingProvider(
        api_key=settings.openai_api_key,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
    return AzureSearchRetrieval(
        documents=load_knowledge(knowledge_directory),
        client=client,
        embeddings=embeddings,
        min_score=settings.azure_search_min_score,
    )
