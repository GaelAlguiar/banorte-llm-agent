# Guion de demostración técnica — 5 minutos

El video debe grabarse sin mostrar variables de entorno, claves, secretos ni
valores de autenticación. Conviene tener abiertas previamente las pestañas de
código, Azure, consumo de OpenAI y la plataforma del reto.

## 0:00–0:30 — Introducción

**Pantalla:** interfaz del agente en la plataforma del reto, sin ejecutar aún
una pregunta.

**Speech:**

> Hola, soy Gael Alguiar. Para este reto construí y desplegué un agente de CV
> que permite conversar sobre mi experiencia, habilidades y proyectos. Mi
> objetivo no fue crear solamente un chatbot con una interfaz atractiva, sino
> demostrar cómo diseñaría un producto de inteligencia artificial que pueda
> integrarse, evaluarse, asegurarse y operarse en un entorno real. La solución
> combina Open Responses, un flujo agéntico, RAG con Azure AI Search, OpenAI y
> Azure Container Apps.

## 0:30–1:15 — Orquestación del agente

**Pantalla:** `cv_agent/agent/service.py`. Mostrar `CvAgentService`,
`_select_skill` y `answer`.

**Speech:**

> El núcleo está separado de la interfaz y del proveedor de infraestructura.
> En este servicio recibo la pregunta, selecciono una skill de forma
> determinista y limito las categorías de conocimiento que esa intención puede
> consultar. Por ejemplo, hay skills para proyectos, arquitectura, ajuste al
> rol, aprendizaje y privacidad. Después recupero evidencia autorizada y se la
> entrego al modelo junto con reglas de respuesta. Esta separación hace que el
> modelo redacte con naturalidad, pero evita usarlo como fuente de hechos. Los
> hechos deben provenir de los documentos sanitizados de mi perfil.

## 1:15–2:05 — Recuperación híbrida

**Pantalla:** `cv_agent/retrieval/azure_search.py`. Señalar `search`,
`VectorizedQuery`, `search_text`, filtros, `top` y `ready`.

**Speech:**

> En producción el agente usa Azure AI Search como motor real de recuperación.
> Para cada pregunta genero un embedding con OpenAI y ejecuto una consulta
> híbrida: envío tanto el texto para BM25 como el vector para similitud
> semántica. Azure fusiona ambos rankings. También aplico filtros por categoría,
> limito el número de resultados y descarto evidencia por debajo de un umbral.
> Elegí búsqueda híbrida porque una consulta puede contener nombres exactos,
> como Terraform o APIM, y al mismo tiempo expresar una intención semántica.
> Así aprovecho precisión léxica y cobertura conceptual. En producción no hay
> fallback silencioso: si Azure no está disponible, la sonda de readiness lo
> refleja en lugar de aparentar que la arquitectura sigue funcionando.

## 2:05–2:45 — Ingesta y aprendizaje controlado

**Pantalla:** `cv_agent/retrieval/ingest.py`. Señalar `build_index`,
`build_search_document` y `sync_documents`.

**Speech:**

> Separé la ingesta del proceso web. Este comando crea o valida el esquema,
> calcula un hash por documento, genera embeddings, actualiza la información
> vigente y elimina registros que dejaron de estar autorizados. Los archivos
> enviados durante una conversación no se agregan automáticamente al índice.
> Esta es una decisión importante: el agente no aprende sin control de cada
> usuario. Mejorarlo implica revisar información, versionarla, ejecutar la
> ingesta, evaluar el resultado y desplegarlo. Eso reduce contaminación de
> datos, prompt injection y respuestas basadas en información no validada.

## 2:45–3:35 — Azure y operación

**Pantalla:** Azure AI Search. Mostrar nombre, estado Running, nivel Free,
ubicación y Search Explorer o el índice `cv-profile-v1`. Después cambiar a
Azure Container Apps y mostrar la revisión activa, la imagen y la identidad.

**Speech:**

> Aquí está la infraestructura desplegada en la suscripción configurada para la demostración. Azure
> AI Search está activo en nivel Free y el índice contiene doce documentos
> autorizados. La API corre en Azure Container Apps como un contenedor sin
> privilegios. Para conectarse al buscador no almacena una clave administrativa:
> utiliza identidad administrada con el rol mínimo Search Index Data Reader.
> La clave administrativa se usa únicamente durante la ingesta y no queda
> disponible para el proceso web. También configuré una sonda
> `/health/ready`, que comprueba el acceso real al índice antes de considerar
> saludable una revisión.

## 3:35–4:05 — OpenAI, seguridad y evaluación

**Pantalla:** consumo de OpenAI. Mostrar actividad sin abrir claves. Después
mostrar brevemente `infra/azure/deploy.sh` en las líneas de SKU Free, RBAC y
readiness.

**Speech:**

> OpenAI se utiliza para embeddings y para generar la respuesta final, pero la
> evidencia se recupera desde Azure AI Search. La aplicación acepta un nivel de
> razonamiento controlado y no reenvía parámetros arbitrarios. Los secretos se
> inyectan en runtime, los logs no guardan preguntas ni documentos y el script
> de despliegue se detiene antes de crear un nivel de Search con costo. La
> solución cuenta con ochenta pruebas automatizadas. La evaluación obtuvo más
> de noventa y cuatro por ciento de Recall at 5, más de noventa y siete por
> ciento de groundedness y cien por ciento en privacidad.

## 4:05–4:45 — Demostración en la plataforma

**Pantalla:** plataforma del reto. Ejecutar estas preguntas; si el tiempo de
respuesta consume demasiado video, mostrar la respuesta ya preparada y
explicar qué valida.

1. `¿Qué experiencia laboral tiene Gael con inteligencia artificial?`
2. `¿Cómo funciona la arquitectura RAG de este agente?`
3. `¿Cuál es la receta de una paella valenciana?`

**Speech mientras se muestran las respuestas:**

> La primera pregunta valida que el agente recupera proyectos laborales,
> responsabilidades e impacto, en lugar de responder con un resumen genérico.
> La segunda explica su propia arquitectura usando la evidencia técnica
> actualizada. Finalmente hago una pregunta fuera del alcance. El agente se
> abstiene porque no existe evidencia autorizada, demostrando que el objetivo
> no es contestar todo, sino responder de forma confiable sobre mi trayectoria.

## 4:45–5:00 — Cierre

**Pantalla:** interfaz del agente con las conversaciones visibles.

**Speech:**

> Este proyecto reúne mi experiencia full stack, integraciones empresariales,
> nube e inteligencia artificial aplicada. También refleja cómo trabajo:
> aprendo con rapidez, documento decisiones, pruebo lo que construyo y llevo
> una idea hasta una solución desplegada y operable. Soy Gael Alguiar y gracias
> por revisar mi agente.

## Pantallas que no deben mostrarse

- `.env` o cualquier vista de secretos;
- claves de OpenAI, Azure o del agente;
- comandos que impriman tokens;
- datos de facturación distintos de la gráfica general de consumo;
- logs completos con información que no haya sido revisada previamente.
