---
id: genai-banorte-agent
title: Agente GenAI con RAG, herramientas y evaluación
category: proyecto
evidence_level: directa
source_kind: demostrativo
source: implementación demostrable del Reto IA Banorte
---
## Problema

Construir un agente capaz de conversar con naturalidad sobre la trayectoria de Gael y, al mismo tiempo, demostrar ingeniería GenAI más allá de una interfaz atractiva.

## Solución

Diseñó una API en Python y FastAPI compatible con Open Responses. El agente consulta una base de conocimiento profesional sanitizada mediante RAG, usa herramientas con argumentos estrictos y produce respuestas breves respaldadas por evidencia.

## Recuperación

La solución incluye ingesta, limpieza, fragmentación, embeddings, búsqueda vectorial, BM25, Reciprocal Rank Fusion, reranking, citas y umbral de relevancia. La capa vectorial está desacoplada para poder migrar a Qdrant, Pinecone, pgvector o Azure AI Search.

## Agentes y protocolos

El proyecto demuestra herramientas, un ciclo agente-herramienta y conceptos de colaboración A2A. La compatibilidad Open Responses permite que otra plataforma consuma el agente mediante un contrato conocido.

## Evaluación y seguridad

Incluye casos de recuperación, fidelidad, estilo, privacidad, selección de herramientas y resistencia a prompt injection. Registra request ID, latencia y métricas sin guardar secretos ni información interna.

## Decisión técnica

Prefirió componentes explícitos y evaluables sobre agregar frameworks innecesarios. Esto permite explicar qué hacen los embeddings, el retrieval y las herramientas debajo de abstracciones como LangChain.
