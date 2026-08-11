import numpy as np

from cv_agent.retrieval.embeddings import OpenAIEmbeddingProvider


def test_openai_embedding_provider_requests_configured_model():
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        model="text-embedding-3-small",
        dimensions=3,
    )
    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        item = type("Item", (), {"embedding": [0.1, 0.2, 0.3]})()
        return type("Response", (), {"data": [item]})()

    provider.client.embeddings.create = create

    result = provider.embed("experiencia con Azure")

    assert np.allclose(result, [0.1, 0.2, 0.3])
    assert captured == {
        "model": "text-embedding-3-small",
        "input": "experiencia con Azure",
        "dimensions": 3,
    }
