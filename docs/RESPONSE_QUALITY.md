# Diseño de respuestas orientadas a impacto

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

1. ¿Por qué la experiencia laboral de Gael lo convierte en un candidato valioso para este puesto de IA Generativa?
2. ¿Qué solución de inteligencia artificial implementó Gael en Enerey y qué impacto tuvo para el negocio y los clientes?
3. ¿Cuál fue el rol de Gael en el proyecto de Banregio y qué experiencia obtuvo trabajando con arquitectura, cloud e infraestructura empresarial?
4. ¿Cómo diseñó Gael un sistema RAG completo y cómo evaluó la calidad, seguridad y fidelidad de sus respuestas?
5. ¿Qué ejemplo demuestra mejor la capacidad de Gael para aprender de forma autónoma y convertir una tecnología nueva en una solución funcional?
6. ¿Cómo combina Gael Python, FastAPI, Flask, APIs y servicios cloud para llevar una solución de IA desde la idea hasta producción?
7. ¿Cómo demuestra Gael su capacidad para diseñar agentes interoperables con herramientas, A2A y Open Responses?
8. ¿Qué aportaría Gael durante sus primeros meses dentro de un equipo de Ingeniería de IA Generativa?
