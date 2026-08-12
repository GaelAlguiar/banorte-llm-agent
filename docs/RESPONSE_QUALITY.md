# Diseño de respuestas orientadas a impacto

## Política profesional y alcance

Toda afirmación sobre Gael procede de evidencia autorizada. El agente puede
explicar conocimiento técnico general relacionado con la vacante, pero separa
esa explicación de la experiencia comprobada. Ante tecnología adyacente usa
evidencia relacionada, fundamentos transferibles, un plan de adopción y
humildad Junior, sin fabricar experiencia. Lo ajeno al perfil recibe una
redirección breve y sin documentos del CV.

Las preguntas conductuales usan STAR únicamente con los cuatro elementos
confirmados. Sin un incidente verificable, muestran el comportamiento más
cercano —depuración, feedback, aprendizaje u ownership— sin inventar anécdotas.

`capability_advisor` y `behavioral_interview` tienen allowlists explícitas y
estrechas. Su fallback de recuperación elimina sólo el filtro de categoría y
conserva la misma allowlist. Cuando ninguna ruta determinista conocida tiene
una coincidencia confiable, un clasificador semántico separado recibe solamente
la pregunta y decide entre perfil, capacidad adyacente, conducta o fuera de
alcance. Usa salida estructurada estricta, razonamiento `none`, máximo 128 tokens,
`store=false` y timeout corto. Las rutas conocidas y las ocho sugerencias lo
evitan, reduciendo costo y latencia. Ante error clasifica fuera de alcance y no
recupera evidencia: prefiere una redirección neutral a filtrar datos del CV o
atribuir experiencia equivocada. La privacidad se clasifica antes y de forma
independiente. `role_fit` puede usar evidencia laboral directa de Enerey y
cotizaciones. Las ocho sugerencias permanecen byte por byte sin cambios.

Cada consulta ambigua que llegue al fallback añade una llamada al modelo y,
por tanto, costo y latencia antes de la generación final. El modelo se puede
configurar con `OPENAI_PROFESSIONAL_CLASSIFIER_MODEL`; si no se define, reutiliza
`OPENAI_MODEL`. No se fija un modelo alternativo por defecto: esa decisión debe
basarse en mediciones de precisión, costo y latencia. La evaluación offline
mide clasificación, routing y recuperación; no califica como perfecta la prosa
generada, que se revisa por separado contra el endpoint productivo.

## Objetivo

AIguiar AI debe responder como un representante profesional de Gael, no como
un inventario de tecnologías. Ante preguntas sobre experiencia, habilidades o
ajuste al puesto, debe seleccionar uno o dos proyectos pertinentes y explicar
qué problema existía, para quién se construyó, qué hizo Gael, qué decisión tomó
y qué resultado produjo.

## Evidencia y estimaciones

Cada afirmación se clasificará internamente en uno de estos niveles:

- **Confirmada:** respaldada por CV, código, documentación o relato directo.
- **Estimada:** aproximación proporcionada por Gael y presentada como tal.
- **Inferida:** beneficio razonable derivado de la solución, expresado sin una
  cifra ni como resultado auditado.

El agente nunca inventará clientes, montos, número de usuarios, porcentajes,
fechas o resultados medidos. Puede usar términos como “aproximadamente”,
“cerca de” o “de forma estimada” cuando corresponda. Si no existe una métrica,
describirá el beneficio cualitativo: menos trabajo manual, mejor trazabilidad,
consulta más sencilla, integración entre sistemas o despliegue más repetible.

## Historia inicial confirmada

### Automatización de cotizaciones masivas

- **Destinatarios:** clientes y equipo responsable del proceso comercial.
- **Problema:** preparar, personalizar y enviar cotizaciones masivas por
  WhatsApp requería cerca de ocho horas de trabajo.
- **Participación:** Gael combinó varias funciones de IA y automatización para
  seleccionar información, apoyar la personalización de mensajes y coordinar
  el flujo de envío.
- **Impacto estimado:** el proceso pasó de aproximadamente ocho horas a una,
  reduciendo tareas manuales y acelerando la atención a clientes.
- **Regla de comunicación:** presentar la reducción como una estimación basada
  en experiencia operativa, no como una métrica auditada.

## Plantilla para proyectos adicionales

Cada proyecto se documentará con los siguientes campos:

1. Nombre reconocible del proyecto.
2. Usuario, área o tipo de destinatario, sin revelar datos confidenciales.
3. Problema operativo o técnico.
4. Responsabilidad concreta de Gael.
5. Tecnologías relevantes, solamente si ayudan a explicar la solución.
6. Decisión o dificultad importante.
7. Impacto confirmado, estimado o inferido.
8. Aprendizaje y relación con el puesto cuando la pregunta lo amerite.

## Comportamiento de respuesta

- Contestar primero la pregunta, sin anunciar búsquedas ni fuentes.
- Priorizar evidencia específica sobre listas de tecnologías.
- Para preguntas amplias, elegir el proyecto con mayor relación semántica.
- Para preguntas comparativas, usar como máximo dos proyectos.
- Mantener un tono natural, seguro y conversacional.
- Evitar repetir nombre completo, cargo y objetivo profesional en cada turno.
- Usar de 80 a 160 palabras como rango normal, ampliándolo si se solicita.
- Cerrar con el resultado o aprendizaje; no agregar frases promocionales
  genéricas que no respondan a la pregunta.

## Recuperación y generación

Las historias se almacenarán como documentos pequeños e independientes para
que el recuperador conserve juntos el problema, la participación y el impacto.
La skill de proyectos exigirá al menos un nombre de proyecto y un resultado.
Las preguntas generales de perfil podrán recuperar tanto el resumen como una
historia concreta para evitar respuestas vagas.

### Experiencia laboral frente a proyectos demostrativos

Los documentos se clasificarán como `laboral`, `demostrativo` o `perfil`. Las
preguntas sobre experiencia profesional deben priorizar historias laborales.
Los proyectos demostrativos, incluido el agente de CV, solo se usarán como
evidencia complementaria o cuando el usuario pregunte por su arquitectura.

La experiencia laboral principal de IA incluirá el ecosistema Enerey: chatbot
integrado en la aplicación, automatizaciones por WhatsApp y cotizaciones
asistidas por IA enviadas a aproximadamente 400 grupos de clientes. El impacto
estimado fue reducir el proceso de cerca de ocho horas a aproximadamente una.

### Recuperación por tecnología exacta

Cuando la pregunta mencione una tecnología presente en evidencia directa, el
recuperador debe incluir y priorizar el documento laboral correspondiente. Una
coincidencia literal como Terraform, APIM, AKS, Entra ID o Firebase no puede
quedar desplazada por un resumen genérico del perfil.

Terraform se documentará como experiencia laboral directa: Gael levantó
infraestructura, creó y utilizó módulos reutilizables, trabajó con variables y
outputs y aplicó estándares y convenciones del entorno Banregio. El agente no
puede responder que Terraform no fue una herramienta principal cuando esta
historia sea pertinente.

## Evaluación

Se añadirán casos que verifiquen:

- presencia de un proyecto identificable;
- explicación del problema y participación;
- impacto concreto o cualitativo;
- lenguaje de aproximación para métricas estimadas;
- ausencia de cifras o hechos no autorizados;
- respuestas naturales que no parezcan una lista de CV.
- prioridad de experiencia laboral sobre proyectos demostrativos;
- recuperación directa para tecnologías mencionadas explícitamente;
- prohibición de negar experiencia respaldada por evidencia directa.

La aceptación requiere que las preguntas de experiencia y ajuste profesional
incluyan evidencia concreta sin degradar las pruebas de privacidad, seguridad,
recuperación y compatibilidad Open Responses existentes.

## Preguntas iniciales alineadas con el puesto

Las interfaces del agente mostrarán ocho preguntas diseñadas para revelar valor
profesional, no solamente conocimientos aislados:

1. ¿Por qué la experiencia laboral de Gael lo convierte en un candidato valioso para un equipo de IA Generativa?
2. ¿Qué proyecto demuestra mejor la experiencia laboral de Gael con inteligencia artificial y qué impacto tuvo?
3. ¿Cómo construyó Gael este agente de CV, qué decisiones tomó en su arquitectura y dónde puedo consultar el código?
4. ¿Cómo participó Gael en el chatbot, el análisis de documentos con IA, el despliegue en AKS y el uso de Vertex AI en HeyTech?
5. ¿Cómo diseñó Gael una fachada segura entre clientes, Azure Functions y APIM?
6. ¿Qué experiencia tiene Gael con Terraform y conectividad multicloud entre Azure, AWS y Google Cloud?
7. ¿Cómo combina Gael backend, frontend, APIs y cloud para llevar soluciones de IA a producción?
8. ¿Qué diferencia a Gael de otros candidatos y qué aportaría durante sus primeros meses en un equipo de IA?
