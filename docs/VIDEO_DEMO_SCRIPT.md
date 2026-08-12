# Guion de demostración técnica — 5 minutos

El video se graba con dos preguntas en vivo. Antes de comenzar, deben estar
abiertas y ordenadas las pestañas indicadas en cada bloque. No se muestran
variables de entorno, secretos, identificadores de suscripción ni valores de
autenticación.

## 0:00–0:25 — Apertura

**Pantalla:** plataforma Reto IA, agente `GAEL ALGUIAR IA`.

> Hola, soy Gael Alguiar. Para este reto construí un agente de CV que permite
> consultar mi experiencia y mis proyectos mediante respuestas fundamentadas
> en evidencia autorizada. Mi objetivo no fue hacer solamente un chatbot, sino
> demostrar una solución de inteligencia artificial que pudiera diseñarse,
> integrarse, desplegarse, evaluarse y operarse. La arquitectura combina el
> protocolo Open Responses, un orquestador por skills, RAG híbrido, OpenAI,
> Azure AI Search y Azure Container Apps.

## 0:25–1:10 — Orquestación y evidencia

**Pantalla:** `cv_agent/agent/service.py`, líneas 387–490.

> Éste es el núcleo del agente. La entrada pasa primero por guardrails de
> privacidad; después se selecciona una skill según la intención: perfil,
> proyecto, arquitectura, ajuste al rol, aprendizaje o comportamiento. Cada
> skill tiene una lista mínima de fuentes autorizadas, de modo que una pregunta
> de arquitectura no obtiene acceso indiscriminado a todo el CV. Luego recupero
> hasta ocho fragmentos relevantes y se los entrego al modelo junto con las
> reglas de respuesta. Así separo dos responsabilidades: Azure aporta los
> hechos y OpenAI redacta la respuesta. Si la pregunta está fuera del propósito
> profesional, el agente redirige sin inventar información.

## 1:10–1:50 — RAG híbrido

**Pantalla:** `cv_agent/retrieval/azure_search.py`, líneas 76–158.

> En producción genero un embedding de la pregunta y hago una búsqueda híbrida.
> En la misma consulta envío texto para BM25 y un vector para similitud
> semántica. Azure fusiona ambos rankings; después aplico filtros por categoría,
> documento y umbral, y diversifico los resultados para evitar que fragmentos
> repetidos desplacen evidencia más útil. Elegí este enfoque porque preguntas
> sobre APIM, Terraform o WhatsApp necesitan coincidencia léxica precisa, pero
> otras expresan la misma experiencia con palabras diferentes y se benefician
> de recuperación semántica.

## 1:50–2:35 — Azure y operación

**Pantalla:** capturas sanitizadas de componentes, Azure AI Search, Container
Apps y Managed Identity.

> La solución está desplegada en Azure Container Apps como un contenedor sin
> privilegios. Azure AI Search contiene diecisiete documentos fuente divididos
> en cincuenta y cuatro chunks temáticos y trazables. La aplicación consulta el
> índice mediante identidad administrada y el rol mínimo Search Index Data
> Reader; la clave administrativa se utiliza únicamente durante la ingesta y
> no queda disponible para la API. También separé liveness de readiness:
> `/health` confirma que el proceso vive y `/health/ready` valida acceso real a
> Search y al almacén del medidor antes de dirigir tráfico a una revisión.

## 2:35–2:55 — OpenAI y control de consumo

**Pantalla:** OpenAI Usage, sin abrir API keys. Después, si hay tiempo,
`cv_agent/usage/meter.py`, líneas 12–85.

> OpenAI se utiliza para embeddings, clasificación semántica y generación
> fundamentada. Para hacer visible y responsable el consumo, cada respuesta
> muestra sus tokens reales y el porcentaje disponible. El cálculo considera
> entrada, caché, escritura de caché y salida; el acumulado se persiste de forma
> atómica en Azure Table Storage. La interfaz nunca muestra dinero, tarifas ni
> secretos y el cliente no puede modificar la contabilidad.

## 2:55–3:45 — Pregunta en vivo: arquitectura y repositorio

**Pantalla:** volver a Reto IA y enviar:

`¿Cómo construyó Gael este agente de CV, qué decisiones tomó y dónde puedo revisar el repositorio y la demostración técnica?`

**Mientras se genera:**

> Esta pregunta valida el proyecto como un sistema completo. La respuesta debe
> explicar el contrato Open Responses, la base de conocimiento sanitizada, el
> flujo de chunking, embeddings, recuperación híbrida, ranking, generación
> aumentada, guardrails, evaluación, despliegue y operación. También debe
> entregar el repositorio público, que permite revisar el código y las
> decisiones técnicas. La evaluación determinista cubre ciento veinticinco
> casos de recuperación y enrutamiento, además de contratos separados para la
> calidad estructural de las respuestas.

**Cuando termine:** señalar el enlace al repositorio y el pie
`N tokens · P% disponible`.

## 3:45–4:35 — Pregunta en vivo: experiencia laboral

**Pantalla:** enviar:

`¿Qué proyecto demuestra mejor la experiencia laboral de Gael con inteligencia artificial y qué impacto tuvo?`

**Mientras se genera:**

> Aquí quiero demostrar que el agente distingue un proyecto laboral de una
> prueba técnica. Debe priorizar Enerey, donde fui el único desarrollador y
> responsable técnico de extremo a extremo. La historia incluye automatización
> de cotizaciones por WhatsApp y el cambio estimado de un proceso de unas ocho
> horas a cerca de una hora. También existen chatbots para seguimiento de
> pedidos y consulta interna desde iOS, pero el agente debe elegir la evidencia
> más fuerte para responder de forma concreta y no listar todo el CV.

**Cuando termine:** señalar la atribución, el impacto marcado como estimado y
el nuevo pie de tokens, cuyo porcentaje debe reflejar el consumo acumulado.

## 4:35–5:00 — Cierre

**Pantalla:** repositorio público o conversación final en Reto IA.

> Este proyecto reúne mi experiencia en backend, frontend, integraciones,
> cloud e inteligencia artificial aplicada. También refleja mi forma de
> trabajar como candidato Junior: partir de fundamentos, construir componentes
> verificables, proteger la información, medir resultados, documentar
> decisiones e iterar con retroalimentación. El repositorio incluye la
> arquitectura, seguridad, evaluación, operación y los límites conocidos de la
> solución. Soy Gael Alguiar; gracias por revisar mi agente.

## Orden de pestañas

1. Reto IA — agente y preguntas en vivo.
2. `service.py` — orquestación, guardrails, skills y evidencia.
3. `azure_search.py` — embeddings y búsqueda híbrida.
4. Componentes Azure — captura sanitizada.
5. Azure AI Search — captura sanitizada.
6. Azure Container Apps — captura sanitizada.
7. Managed Identity y RBAC — captura sanitizada.
8. OpenAI Usage — actividad general, nunca claves.
9. `usage/meter.py` — contador por respuesta.
10. Repositorio — cierre y futura liga del video.

## No mostrar

- `.env`, secretos, API keys o valores de autenticación;
- identificadores de cuenta, tenant o suscripción;
- direcciones privadas, nombres internos o topología sensible;
- importes monetarios del presupuesto interno del medidor;
- correos, mensajes u otras pestañas ajenas a la demostración.
