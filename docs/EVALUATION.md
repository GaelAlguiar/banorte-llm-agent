# Evaluación

`evals/cv_agent_cases.jsonl` contiene 94 casos en español: perfil, experiencia, proyectos, arquitectura, ajuste a la vacante, habilidades adyacentes, aprendizaje, privacidad, prompt injection y fuera de alcance. La cobertura empresarial incluye una fachada segura con Azure Functions, APIM y Managed Identity; Terraform modular y conectividad entre Azure, AWS y Google Cloud; análisis de documentos PDF con Python sobre Azure; entrega coordinada mediante Jira; seguimiento autorizado de pedidos por un chatbot de WhatsApp; consulta operativa autorizada desde un chatbot interno en la aplicación iOS de Enerey; trabajo freelance en los sitios Global y Lugra como fuente independiente; términos técnicos de doble uso como token y prompt; distinción entre explicaciones educativas, preventivas y solicitudes ambiguas o privadas; casos adversariales donde lenguaje educativo no oculta una extracción en la misma consulta; preguntas profesionales posteriores que permanecen permitidas; y rechazo de solicitudes de rutas, URLs, rangos de red, contraseñas, credenciales o instrucciones internas. La ejecución offline sustituye la llamada semántica por un clasificador determinista conservador basado en intención, no por respuestas asociadas a preguntas exactas. Esto permite comprobar paráfrasis nuevas sin red ni credenciales; no pretende medir la calidad del modelo productivo, que requiere evaluación live separada.

La evaluación offline utiliza un adaptador determinista que devuelve los extractos de evidencia recuperados; no genera prosa con un LLM. Así mide recuperación y routing sin que la variabilidad o costo del modelo oculten regresiones. Las métricas son Recall@5, MRR, groundedness por evidencia, privacidad, `evidence_term_coverage`, routing y percentiles de latencia. `evidence_term_coverage` sólo comprueba términos requeridos y prohibidos en la evidencia, no estilo, tono ni calidad de una respuesta generada.

Los casos sin documentos esperados sólo aprueban recuperación y groundedness cuando la respuesta tampoco expone evidencia. `impact_evidence_coverage` se calcula exclusivamente sobre los casos marcados con `requires_impact_story`; cada uno declara `impact_terms` y debe recuperar toda la evidencia esperada, cubrir sus términos requeridos y prohibidos, y contener al menos un término de impacto respaldado. No valida la narrativa del modelo.

El adaptador offline conserva el mismo contrato que Azure AI Search, pero no
pretende sustituir la prueba productiva. El tono, la afirmación correcta de
participación confirmada y la redacción final deben verificarse manualmente
contra el endpoint live. Después del despliegue se ejecutan los
casos de `evals/azure_search_cases.jsonl` contra el endpoint público y se valida
`/health/ready` para demostrar que Azure atendió las consultas.

```bash
python -m cv_agent.evaluation.runner
```

El reporte local se escribe en `outputs/cv_agent_evaluation.json` y se ignora en Git. CI vuelve a ejecutar la matriz desde cero. Esta evaluación no sustituye pruebas humanas ni evaluación del modelo; para producción se agregarían jueces calibrados, conjuntos reales anonimizados, análisis de alucinación y monitoreo de drift.
