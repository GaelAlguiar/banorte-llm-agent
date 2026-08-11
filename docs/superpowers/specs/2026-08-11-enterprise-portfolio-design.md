# Diseño de ampliación del portafolio empresarial

## Objetivo

Ampliar el agente de CV con historias profesionales de HeyTech y Banregio que
permitan explicar con precisión los problemas abordados, la participación de
Gael, las decisiones técnicas, las tecnologías utilizadas y el impacto. La
información debe mejorar la profundidad de las respuestas sin publicar código
propietario, secretos ni detalles operativos sensibles.

## Alcance

La ampliación cubrirá siete áreas:

1. Fachada Java ejecutada en Azure Functions delante de Azure API Management.
2. Infraestructura modular de Azure construida con Terraform.
3. Conectividad VPN Site-to-Site entre Azure, AWS y Google Cloud.
4. Chatbot empresarial de HeyTech y su orquestación con servicios internos.
5. Análisis de constancias y comprobantes PDF con servicios de IA en Python.
6. Ecosistema complementario de pagos, microservicios Java, seguridad cloud,
   políticas de APIM y dashboard Angular.
7. Planeación y seguimiento en Jira mediante historias, subtareas,
   dependencias, bloqueos y entregables por sprint.

Quedan fuera del alcance el código fuente empresarial, configuraciones de red,
credenciales, tokens, URLs internas, nombres de personas, identificadores de
recursos y cualquier detalle que permita reconstruir la topología privada.

## Procedencia y nivel de evidencia

Cada historia tendrá una procedencia explícita:

- **Autoría verificable:** existe un Pull Request asociado a la cuenta
  `jorge-alguiar_ris` que respalda la contribución.
- **Participación confirmada:** Gael confirmó su participación laboral, aunque
  los cambios hayan sido publicados por otra persona o cuenta.

El agente podrá mencionar HeyTech y Banregio. No atribuirá a Gael la autoría
exclusiva de un repositorio completo ni afirmará métricas cuantitativas que no
estén documentadas. Cuando no exista una métrica auditada, describirá el
impacto de forma cualitativa.

## Modelo de las historias

Cada historia de conocimiento contendrá:

1. Nombre reconocible del proyecto o área.
2. Contexto y problema empresarial.
3. Participación concreta de Gael.
4. Arquitectura y componentes principales a nivel público.
5. Decisiones técnicas y consideraciones de seguridad.
6. Tecnologías utilizadas.
7. Resultado o impacto confirmado/inferido.
8. Procedencia de la evidencia.

El agente seleccionará una o dos historias pertinentes para cada respuesta. No
responderá con una lista extensa de tecnologías cuando una historia concreta
pueda explicar mejor la experiencia.

## Historias profesionales

### Fachada segura para APIM

La historia explicará la construcción de una Azure Function en Java como
fachada previa a APIM. Incluirá autenticación basada en JWT, Managed Identity,
resolución dinámica y protegida de suscripciones, enrutamiento, filtrado de
encabezados, pruebas y documentación. Se describirá como autoría verificable.

### Terraform modular en Azure

La historia mostrará la separación de infraestructura por dominios técnicos:
red, aplicaciones, datos, IAM, seguridad, bastion, Redis y recursos
compartidos. Incluirá validación de Terraform, documentación de arquitectura y
configuración por ambiente. Se describirá como autoría verificable.

### VPN multicloud

La historia explicará el diseño modular de VPN Site-to-Site Azure-AWS y
Azure-GCP, incluyendo gateways, BGP, rutas, recursos por ambiente y validación
de conectividad, sin publicar rangos de red ni identificadores. Se describirá
como autoría verificable.

### Chatbot HeyTech

La historia presentará la participación en comunicación y orquestación del
chatbot empresarial, su integración con APIM y servicios internos y las
consideraciones de seguridad y operación. Se describirá como participación
confirmada.

### Análisis de documentos con IA

La historia agrupará los servicios para constancias y comprobantes PDF. Se
explicará el uso de Python, contenedores, pruebas, persistencia y despliegue en
Azure sin mencionar feeds privados, rutas internas o secretos. Se describirá
como participación confirmada.

### Ecosistema HeyTech

La historia conectará el trabajo en pagos, microservicios y librerías Java,
seguridad y guardrails cloud, políticas de APIM y dashboard Angular. Su
propósito será demostrar visión de plataforma y colaboración entre frontend,
backend, infraestructura y seguridad. Se describirá como participación
confirmada.

### Entrega ágil con Jira

La historia explicará el uso de Jira para registrar historias de usuario,
dividir trabajo en subtareas, gestionar dependencias y bloqueos y dar
seguimiento a pruebas, documentación y entregables dentro de cada sprint. Se
describirá como participación confirmada.

## Preguntas sugeridas

La interfaz propia y la plataforma externa usarán las mismas ocho preguntas:

1. ¿Qué proyectos empresariales demuestran mejor la experiencia de Gael con
   IA, cloud e integración?
2. ¿Cómo diseñó Gael una fachada segura entre clientes, Azure Functions y
   APIM?
3. ¿Qué experiencia tiene Gael construyendo infraestructura modular con
   Terraform en Azure?
4. ¿Cómo implementó conectividad multicloud entre Azure, AWS y Google Cloud?
5. ¿Qué participación tuvo Gael en el chatbot y los servicios de análisis de
   documentos con IA de HeyTech?
6. ¿Cómo trabajó Gael con microservicios Java, seguridad cloud, pagos y
   políticas de APIM?
7. ¿Cómo organizaba Gael historias, subtareas, dependencias y entregables
   mediante Jira en cada sprint?
8. ¿Por qué esta experiencia convierte a Gael en un candidato valioso para un
   equipo de IA empresarial?

## Flujo de datos

Los nuevos documentos se cargarán mediante el cargador de conocimiento
existente. En local, el índice determinista permitirá ejecutar pruebas sin
dependencias externas. En Azure, el proceso de ingesta actualizará el índice
`cv-profile-v1`; el endpoint Open Responses recuperará las historias
pertinentes y el modelo generará la respuesta respetando las instrucciones y
guardrails existentes.

La actualización de prompts sugeridos es independiente del conocimiento: se
modificará la plantilla Flask y, después de validar el endpoint desplegado, se
sincronizarán manualmente las mismas ocho preguntas en la configuración del
agente de la plataforma.

## Calidad de respuesta

Las instrucciones exigirán que una respuesta de experiencia incluya, cuando
sea pertinente:

- proyecto o área identificable;
- problema o necesidad;
- participación de Gael;
- dos o tres decisiones o componentes técnicos;
- resultado o impacto;
- lenguaje natural y directo.

Las respuestas distinguirán trabajo personal de trabajo de equipo. Ante una
pregunta confidencial, el agente ofrecerá una explicación arquitectónica sin
revelar información protegida.

## Validación

Se añadirán pruebas para verificar:

- carga y recuperación de las nuevas historias;
- presencia de ocho prompts idénticos en la interfaz;
- respuestas fundamentadas sobre APIM, Terraform, VPN, chatbot, documentos,
  Java, seguridad y Jira;
- distinción entre autoría verificable y participación confirmada;
- ausencia de URLs internas, credenciales, identificadores y marcadores de
  secretos;
- rechazo de solicitudes de información confidencial;
- compatibilidad con el contrato Open Responses y streaming existente.

También se ampliará el conjunto de evaluación y se ejecutarán todas las
pruebas automatizadas antes de desplegar.

## Publicación y operación

Los cambios se desarrollarán en `agent/enterprise-portfolio`, se publicarán en
un Pull Request y se integrarán a `main` después de que CI sea exitoso. Luego
se construirá y desplegará una nueva imagen en Azure Container Apps, se
reindexará el conocimiento autorizado en Azure AI Search y se validarán salud,
disponibilidad y respuestas del endpoint público. Finalmente se actualizarán
los prompts sugeridos en la plataforma sin modificar claves o parámetros
sensibles.

## Criterios de aceptación

1. El agente responde con historias específicas en lugar de descripciones
   vagas.
2. Las siete áreas empresariales son recuperables mediante RAG.
3. Las ocho preguntas sugeridas coinciden entre la interfaz y la plataforma.
4. No se publica información confidencial procedente de los repositorios
   privados.
5. Las pruebas y evaluaciones pasan antes del despliegue.
6. El endpoint público conserva compatibilidad con Open Responses.
