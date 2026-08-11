# Evaluación

`evals/cv_agent_cases.jsonl` contiene 40 casos en español: perfil, experiencia, proyectos, arquitectura, ajuste a la vacante, habilidades adyacentes, aprendizaje, privacidad, prompt injection y fuera de alcance.

La evaluación offline utiliza un adaptador determinista sobre el retrieval real. Así mide recuperación y routing sin que la variabilidad o costo del LLM oculten regresiones. Las métricas son Recall@5, MRR, groundedness por evidencia, términos requeridos/prohibidos, privacidad, estilo, routing y percentiles de latencia.

```bash
python -m cv_agent.evaluation.runner
```

El reporte local se escribe en `outputs/cv_agent_evaluation.json` y se ignora en Git. CI vuelve a ejecutar la matriz desde cero. Esta evaluación no sustituye pruebas humanas ni evaluación del modelo; para producción se agregarían jueces calibrados, conjuntos reales anonimizados, análisis de alucinación y monitoreo de drift.
