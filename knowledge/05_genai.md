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

La solución desplegada usa Azure AI Search Free como índice real. Una ingesta
controlada genera embeddings con OpenAI, sincroniza únicamente los documentos
autorizados y elimina registros obsoletos. Cada pregunta combina búsqueda
textual BM25 y búsqueda vectorial; Azure fusiona ambos rankings y el agente
aplica filtros por categoría y un umbral de relevancia.

Azure Container Apps consulta el índice mediante identidad administrada y el
rol mínimo `Search Index Data Reader`. La sonda `/health/ready` comprueba que el
índice se encuentra disponible. En producción no existe fallback silencioso;
el motor determinista local se limita a pruebas y evaluación offline.

## Agentes y protocolos

El proyecto demuestra herramientas, un ciclo agente-herramienta y conceptos de colaboración A2A. La compatibilidad Open Responses permite que otra plataforma consuma el agente mediante un contrato conocido.

## Evaluación y seguridad

Incluye casos de recuperación, fidelidad, estilo, privacidad, selección de herramientas y resistencia a prompt injection. Registra request ID, latencia y métricas sin guardar secretos ni información interna.

La implementación cuenta con pruebas de configuración, embeddings, consulta
híbrida, filtros, readiness, ingesta, RBAC y controles para impedir que el
despliegue cambie automáticamente a un nivel de pago.

## Decisión técnica

Prefirió componentes explícitos y evaluables sobre agregar frameworks innecesarios. Esto permite explicar qué hacen los embeddings, el retrieval y las herramientas debajo de abstracciones como LangChain.
