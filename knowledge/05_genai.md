---
id: genai-banorte-agent
title: Agente GenAI con RAG, herramientas y evaluación
category: proyecto
evidence_level: directa
source_kind: demostrativo
source: implementación demostrable del Reto IA Banorte
---
La arquitectura incluye RAG, chunking, embeddings, recuperación híbrida,
ranking, generación aumentada, tools, evaluación, guardrails y observabilidad.
También demuestra fundamentos transferibles para integración entre agentes por
A2A y exposición controlada de herramientas mediante MCP; estos dos últimos se
describen como diseño relacionado, no como adopción productiva atribuida.

## Problema

Construir un agente capaz de conversar con naturalidad sobre la trayectoria de Gael y, al mismo tiempo, demostrar ingeniería GenAI más allá de una interfaz atractiva.

## Solución

Diseñó una API en Python y FastAPI compatible con Open Responses. El agente consulta una base de conocimiento profesional sanitizada mediante RAG, usa herramientas con argumentos estrictos y produce respuestas breves respaldadas por evidencia.

## Flujo end-to-end

El flujo usa chunking curado por unidad temática, embeddings de OpenAI y Azure
AI Search para retrieval híbrido con BM25, similitud vectorial y ranking. Las
skills resuelven routing y restringen fuentes; OpenAI realiza la generación
aumentada sólo con evidencia permitida. Antes del retrieval se aplican
guardrails de privacidad. Pruebas y evaluación verifican recuperación, routing
y seguridad. El contenedor opera en Azure Container Apps con `/health`,
`/health/ready` y observabilidad de request ID, estado y latencia sin registrar
prompts ni secretos.

## Recuperación

Para este alcance, el chunking se resolvió durante la curación: cada archivo
Markdown autorizado representa una unidad temática con metadatos y un ID
estable. No se aplica partición dinámica en runtime. Esta decisión simplifica
la trazabilidad y evita fragmentos sin contexto; para documentos extensos se
incorporaría una estrategia de chunks con solapamiento y evaluación específica.

La solución desplegada usa Azure AI Search Free como índice real. Una ingesta
controlada genera embeddings con OpenAI, sincroniza únicamente los documentos
autorizados y elimina registros obsoletos. Cada pregunta combina búsqueda
textual BM25 y búsqueda vectorial; Azure fusiona ambos rankings y el agente
aplica filtros por categoría y un umbral de relevancia.

Azure Container Apps consulta el índice mediante identidad administrada y el
rol mínimo `Search Index Data Reader`. La sonda `/health/ready` comprueba que el
índice se encuentra disponible. En producción no existe fallback silencioso;
el motor determinista local se limita a pruebas y evaluación offline.

El ranking combina BM25 y similitud vectorial en la consulta híbrida de Azure
AI Search. Después, las skills aplican routing, categorías y allowlists de
fuentes antes de entregar la evidencia al modelo de OpenAI para la generación
aumentada. Los guardrails clasifican privacidad antes del retrieval y fallan
cerrado si la clasificación semántica no puede completarse.

## Agentes y protocolos

El proyecto demuestra herramientas, un ciclo agente-herramienta y conceptos de colaboración A2A. La compatibilidad Open Responses permite que otra plataforma consuma el agente mediante un contrato conocido.

## Evaluación y seguridad

Incluye casos de recuperación, fidelidad, estilo, privacidad, selección de herramientas y resistencia a prompt injection. Registra request ID, latencia y métricas sin guardar secretos ni información interna.

La implementación cuenta con pruebas de configuración, embeddings, consulta
híbrida, filtros, readiness, ingesta, RBAC y controles para impedir que el
despliegue cambie automáticamente a un nivel de pago.

La aplicación se desplegó como contenedor sin privilegios en Azure Container
Apps. Para operación expone `/health` y `/health/ready`; la observabilidad
registra sólo metadatos allowlistados como request ID, ruta, estado y latencia,
sin prompts, evidencia ni secretos. El trade-off elegido favorece componentes
explícitos, trazabilidad y evaluación reproducible sobre mayor automatización.

## Decisión técnica

Prefirió componentes explícitos y evaluables sobre agregar frameworks innecesarios. Esto permite explicar qué hacen los embeddings, el retrieval y las herramientas debajo de abstracciones como LangChain.
