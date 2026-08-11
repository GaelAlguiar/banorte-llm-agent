import hashlib
import re
from typing import Protocol

import numpy as np
from openai import OpenAI

from cv_agent.retrieval.text import normalize_text


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> np.ndarray:
        ...


class LocalEmbeddingProvider:
    """Deterministic feature hashing for local tests and evaluation."""

    def __init__(self, dimensions: int = 1024):
        self.dimensions = dimensions

    def embed(self, text: str) -> np.ndarray:
        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            normalize_text(text),
        ).strip()
        features = normalized.split()
        compact = normalized.replace(" ", "_")
        features.extend(
            compact[index:index + 3]
            for index in range(max(0, len(compact) - 2))
        )
        vector = np.zeros(self.dimensions, dtype=np.float32)
        for feature in features:
            digest = hashlib.blake2b(
                feature.encode("utf-8"),
                digest_size=8,
            ).digest()
            vector[int.from_bytes(digest, "big") % self.dimensions] += 1
        norm = np.linalg.norm(vector)
        return vector if norm == 0 else vector / norm


class OpenAIEmbeddingProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        dimensions: int,
    ):
        self.client = OpenAI(api_key=api_key, timeout=30.0)
        self.model = model
        self.dimensions = dimensions

    def embed(self, text: str) -> np.ndarray:
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
            dimensions=self.dimensions,
        )
        return np.asarray(response.data[0].embedding, dtype=np.float32)
