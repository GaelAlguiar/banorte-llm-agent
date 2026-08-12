# Evaluación

`evals/cv_agent_cases.jsonl` contiene 125 casos en español: perfil, experiencia, proyectos, arquitectura, ajuste a la vacante, habilidades adyacentes, conducta, aprendizaje, privacidad, prompt injection y fuera de alcance. La cobertura empresarial incluye una fachada segura con Azure Functions, APIM y Managed Identity; Terraform modular y conectividad entre Azure, AWS y Google Cloud; análisis de documentos PDF con Python sobre Azure; entrega coordinada mediante Jira; seguimiento autorizado de pedidos por un chatbot de WhatsApp; consulta operativa autorizada desde un chatbot interno en la aplicación iOS de Enerey; trabajo freelance en los sitios Global y Lugra como fuente independiente; términos técnicos de doble uso como token y prompt; distinción entre explicaciones educativas, preventivas y solicitudes ambiguas o privadas; casos adversariales donde lenguaje educativo no oculta una extracción en la misma consulta; preguntas profesionales posteriores que permanecen permitidas; y rechazo de solicitudes de rutas, URLs, rangos de red, contraseñas, credenciales o instrucciones internas. La ejecución offline sustituye la llamada semántica por un clasificador determinista conservador basado en intención, no por respuestas asociadas a preguntas exactas. Las reglas de prueba evalúan primero cualquier cláusula de extracción y sólo después reconocen prevención o educación, por lo que una solicitud mixta siempre se considera sensible. Esto permite comprobar paráfrasis nuevas sin red ni credenciales; no pretende medir la calidad del modelo productivo, que requiere evaluación live separada.

La evaluación offline utiliza un adaptador determinista que devuelve los extractos de evidencia recuperados; no genera prosa con un LLM. Así mide exclusivamente clasificación de intención, routing y recuperación sin que la variabilidad o costo del modelo oculten regresiones. Una puntuación de `1.0` en esta matriz no afirma que la prosa generada tenga calidad perfecta; esa redacción se valida por separado con el modelo productivo en una etapa posterior. Las métricas son Recall@8, precisión de evidencia@8, MRR, groundedness por evidencia, privacidad, `evidence_term_coverage`, routing y percentiles de latencia. `evidence_term_coverage` sólo comprueba términos requeridos y prohibidos en la evidencia, no estilo, tono ni calidad de una respuesta generada. Además exige cero fallos en casos core/must-pass (son core por defecto) y un piso de aprobación de 90% por categoría, para que un promedio global no oculte una familia débil.

Los casos sin documentos esperados sólo aprueban recuperación y groundedness cuando la respuesta tampoco expone evidencia. `impact_evidence_coverage` se calcula exclusivamente sobre los casos marcados con `requires_impact_story`; cada uno declara `impact_terms` y debe recuperar toda la evidencia esperada, cubrir sus términos requeridos y prohibidos, y contener al menos un término de impacto respaldado. No valida la narrativa del modelo.

Las pruebas de recuperación también cubren contenido situado después del antiguo
límite de 1200 caracteres: Firebase/Maps/Sheets en Enerey, operación y
observabilidad del agente RAG e impacto de HeyTech. Los allowlists continúan
comparándose contra el `document_id` padre, mientras `chunk_id` permite auditar
la sección exacta. Las pruebas de contrato verifican que la trazabilidad no
exponga rutas locales, URLs privadas ni scores precisos.
También se comprueba que cada chunk respete el límite, que una sección extensa
conserve sus términos finales mediante partes estables y que todos los valores
de `metadata` sean strings de no más de 512 caracteres.

El adaptador offline conserva el mismo contrato que Azure AI Search, pero no
pretende sustituir la prueba productiva. CI verifica que los casos Azure no
queden huérfanos y prueba el adaptador con scores RRF realistas y clientes
falsos, sin consultar Azure. La precisión de evidencia@8 mide contaminación
por padres inesperados y complementa Recall@8 y los pisos por categoría.
El tono, la afirmación correcta de
participación confirmada y la redacción final deben verificarse manualmente
contra el endpoint live. Después del despliegue se ejecutan los
casos de `evals/azure_search_cases.jsonl` contra el endpoint público y se valida
`/health/ready` para demostrar que Azure atendió las consultas.

## Contratos de respuesta offline

`evals/response_contract_cases.jsonl` es una segunda capa, independiente de
`EvidenceModel`. Contiene respuestas representativas curadas y deterministas;
no contiene prosa generada por OpenAI ni intenta simular la distribución de un
modelo. Comprueba propiedades observables de respuestas sobre experiencia y
proyectos directos, ajuste humilde al rol Junior, tecnología adyacente o
desconocida, conducta con STAR sólo cuando está confirmado, seguridad y
privacidad, redirección fuera de alcance y comparaciones multimodales de
vacante, CV, proyecto y arquitectura.

Cada fixture declara su procedencia autorizada, términos necesarios y
prohibidos, etiquetas de experiencia directa, relacionada o transferible
cuando aplican, y elementos de problema, acción y resultado cuando la evidencia
los respalda. El evaluador también rechaza boilerplate negativo ante evidencia
autorizada, afirmaciones senior, detalles inventados o sensibles, respuestas
indirectas y estructuras innecesariamente extensas. Exige cero fallos core y
un piso de 90% por categoría.

La cobertura conductual contiene ambos límites: una historia técnica confirmada
que exige los cuatro elementos STAR y una pregunta de conflicto/liderazgo sin
anécdota confirmada que prohíbe emitir etiquetas STAR o inventar el incidente.
La detección de detalles sensibles reconoce direcciones privadas RFC 1918 en
los rangos completos `10/8`, `172.16/12` y `192.168/16`, valida cada dirección
antes de clasificarla y no bloquea texto con direcciones públicas o inválidas.

```bash
python -m cv_agent.evaluation.runner
python -m cv_agent.evaluation.response_contracts
```

Los reportes locales se escriben en `outputs/cv_agent_evaluation.json` y
`outputs/response_contract_evaluation.json`; ambos se ignoran en Git. Un
resultado perfecto en contratos significa solamente que los fixtures curados
cumplen la política codificada. Antes de liberar cambios de respuesta sigue
siendo obligatorio un smoke productivo de una sola consulta contra el endpoint
live, con OpenAI real, para revisar respuesta directa, atribución, tono Junior,
ausencia de invenciones y trazabilidad. Esta evaluación no sustituye pruebas
humanas ni evaluación del modelo; para producción se agregarían jueces
calibrados, conjuntos reales anonimizados, análisis de alucinación y monitoreo
de drift.
