import argparse
import hashlib
import json
import os
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

from cv_agent.knowledge.loader import load_knowledge_chunks
from cv_agent.knowledge.models import KnowledgeDocument
from cv_agent.retrieval.embeddings import (
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
)


def build_index(index_name: str, dimensions: int) -> SearchIndex:
    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SimpleField(
            name="document_id",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="chunk_id",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchableField(
            name="section",
            type=SearchFieldDataType.String,
        ),
        SearchableField(
            name="title",
            type=SearchFieldDataType.String,
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
        ),
        SimpleField(
            name="category",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="evidence_level",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="impact_type",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="source_kind",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="source",
            type=SearchFieldDataType.String,
        ),
        SimpleField(
            name="content_hash",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(
                SearchFieldDataType.Single
            ),
            searchable=True,
            vector_search_dimensions=dimensions,
            vector_search_profile_name="profile-hnsw",
        ),
    ]
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw")],
        profiles=[
            VectorSearchProfile(
                name="profile-hnsw",
                algorithm_configuration_name="hnsw",
            )
        ],
    )
    return SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
    )


def build_search_document(
    document: KnowledgeDocument,
    embeddings: EmbeddingProvider,
) -> dict:
    vector_text = f"{document.title}\n{document.text}"
    return {
        "id": document.index_id,
        "document_id": document.parent_id,
        "chunk_id": document.index_id,
        "section": document.section,
        "title": document.title,
        "content": document.text,
        "category": document.category,
        "evidence_level": document.evidence_level,
        "impact_type": document.impact_type,
        "source_kind": document.source_kind,
        "source": document.source,
        "content_hash": hashlib.sha256(
            vector_text.encode("utf-8")
        ).hexdigest(),
        "content_vector": [
            float(value)
            for value in embeddings.embed(vector_text)
        ],
    }


def _ensure_succeeded(results, operation: str) -> None:
    if any(not item.succeeded for item in results):
        raise RuntimeError(f"Azure rechazó la {operation} de documentos")


def sync_documents(
    *,
    client,
    documents: list[KnowledgeDocument],
    embeddings: EmbeddingProvider,
) -> dict[str, int]:
    payload = [
        build_search_document(document, embeddings)
        for document in documents
    ]
    current_ids = {item["id"] for item in payload}
    indexed_ids = {
        item["id"]
        for item in client.search(
            search_text="*",
            select=["id"],
            top=1000,
        )
    }
    _ensure_succeeded(
        client.upload_documents(documents=payload),
        "carga",
    )
    stale = [
        {"id": identifier}
        for identifier in sorted(indexed_ids - current_ids)
    ]
    if stale:
        _ensure_succeeded(
            client.delete_documents(documents=stale),
            "eliminación",
        )
    return {"uploaded": len(payload), "deleted": len(stale)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--knowledge", type=Path, default=Path("knowledge"))
    args = parser.parse_args()
    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    index_name = os.getenv("AZURE_SEARCH_INDEX", "cv-profile-v1")
    admin_key = os.environ["AZURE_SEARCH_ADMIN_KEY"]
    openai_key = os.environ["OPENAI_API_KEY"]
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
    credential = AzureKeyCredential(admin_key)
    index_client = SearchIndexClient(endpoint, credential)
    index_client.create_or_update_index(
        build_index(index_name, dimensions)
    )
    client = SearchClient(endpoint, index_name, credential)
    embeddings = OpenAIEmbeddingProvider(
        api_key=openai_key,
        model=model,
        dimensions=dimensions,
    )
    summary = sync_documents(
        client=client,
        documents=load_knowledge_chunks(args.knowledge),
        embeddings=embeddings,
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
