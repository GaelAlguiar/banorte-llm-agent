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
El agente de CV actual está desplegado en Azure Container Apps y opera con
Azure AI Search como índice híbrido. Expone `/health` para salud del proceso y
`/health/ready` para comprobar acceso efectivo al índice antes de atenderse
como listo.

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

La ingesta interpreta los encabezados Markdown y convierte los documentos
extensos en fragmentos temáticos estables. Cada chunk conserva el ID del
documento padre, ruta de procedencia, título, sección y metadatos de evidencia;
los documentos pequeños permanecen completos para no perder contexto. Así la
generación recibe el pasaje localizado que respondió a la consulta, incluso si
aparece al final de la fuente, en vez de truncar siempre el inicio del archivo.

La solución desplegada usa Azure AI Search Free con 53 chunks dinámicos por
sección en esta entrega. La ingesta calcula los fragmentos desde el contenido
versionado, genera embeddings con OpenAI, sincroniza sólo fuentes autorizadas y
elimina chunks obsoletos; la cifra no es una constante operativa. Cada consulta
combina BM25 y búsqueda vectorial, filtros por categoría y relevancia.

Azure Container Apps consulta el índice mediante identidad administrada y el
rol mínimo `Search Index Data Reader`. La sonda `/health/ready` comprueba que el
índice se encuentra disponible. En producción no existe fallback silencioso;
el motor determinista local se limita a pruebas y evaluación offline.

El ranking combina BM25 y similitud vectorial en la consulta híbrida de Azure
AI Search. Después, las skills aplican routing, categorías y allowlists de
fuentes antes de entregar la evidencia al modelo de OpenAI para la generación
aumentada. Los guardrails clasifican privacidad antes del retrieval y fallan
cerrado si la clasificación semántica no puede completarse.

Los resultados se diversifican por documento padre para evitar secciones
repetitivas, aunque una pregunta compuesta puede recuperar dos secciones
distintas del mismo proyecto. La respuesta conserva trazabilidad interna por
`document_id` y `chunk_id`, y expone sólo metadatos no sensibles: título,
sección, tipo y nivel de evidencia, impacto, confianza por rango y, cuando está
autorizada, una URL pública. No publica rutas locales ni scores precisos.

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
