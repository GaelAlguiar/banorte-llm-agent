# Diseño de integración con Azure AI Search

## Objetivo

Reemplazar el índice en memoria utilizado por la aplicación desplegada con un
índice híbrido real en Azure AI Search. La solución debe recuperar evidencia
del perfil mediante búsqueda textual y vectorial, conservar el contrato Open
Responses y evitar que una falla de Azure quede oculta por un fallback local.

El despliegue se realizará en la suscripción `Enerey-Prod`, dentro del grupo de
recursos `rg-prueba-b-gael-ai`. Se intentará utilizar el nivel Free. Si ese
nivel no se encuentra disponible, el proceso debe detenerse antes de crear un
servicio con costo.

## Arquitectura

La aplicación conservará una interfaz de recuperación común con dos
implementaciones:

- Azure AI Search será la implementación obligatoria cuando
  `APP_ENV=production`.
- El índice determinista local se conservará para desarrollo, pruebas unitarias
  y evaluación sin red.

No habrá fallback silencioso de Azure al índice local en producción. Una
configuración incompleta o un servicio indisponible debe reflejarse en la sonda
de disponibilidad y en un error controlado, para que la operación no reporte
una arquitectura distinta de la que realmente atiende las consultas.

## Índice y documentos

El índice almacenará un registro por documento autorizado de `knowledge/` con
los siguientes campos:

- identificador estable;
- título y contenido;
- categoría;
- tipo de fuente;
- nivel de evidencia;
- tipo de impacto;
- referencia de origen;
- hash del contenido;
- vector del título y contenido.

El vector se generará con `text-embedding-3-small`. La dimensión se declarará
en configuración para que el esquema y el cliente se validen entre sí. Los
campos de texto admitirán búsqueda léxica y los metadatos relevantes admitirán
filtros.

## Ingesta

La ingesta será un comando explícito y reproducible, separado del arranque de
la API. El comando deberá:

1. leer únicamente los documentos autorizados;
2. calcular el hash y los embeddings;
3. crear o validar el esquema del índice;
4. cargar o actualizar los documentos;
5. eliminar del índice los documentos que ya no estén autorizados;
6. emitir un resumen sin incluir secretos ni el contenido completo.

Los archivos adjuntos por usuarios no se incorporarán automáticamente. Cambiar
la base profesional seguirá requiriendo revisión, control de versiones,
evaluación e ingesta.

## Recuperación

Cada consulta producirá un embedding y ejecutará una búsqueda híbrida que
combine:

- coincidencia textual de Azure AI Search;
- similitud vectorial;
- filtros opcionales por categoría;
- un límite de resultados entre uno y ocho.

El adaptador convertirá los resultados de Azure al modelo `RetrievalHit` que ya
consume el agente. El umbral de relevancia continuará evitando respuestas
basadas en evidencia débil. Los identificadores, puntajes y metadatos se
conservarán para evaluación y trazabilidad, sin exponer información sensible.

## Seguridad

Azure Container Apps utilizará su identidad administrada para consultar el
índice. La identidad recibirá solamente el rol de lectura de datos requerido
por Azure AI Search. La creación del esquema y la ingesta se ejecutarán como
una operación administrativa separada; las credenciales administrativas no se
guardarán en la imagen ni estarán disponibles para el proceso web.

Las claves de OpenAI permanecerán como secretos de Container Apps. Los logs no
registrarán prompts, vectores, contenido completo, encabezados de autorización
ni secretos.

## Disponibilidad y errores

`/health` continuará indicando que el proceso está activo. Una sonda adicional
`/health/ready` verificará que la configuración de producción exista y que el
índice pueda consultarse. Un problema de autenticación, red o esquema devolverá
una respuesta controlada y quedará registrado mediante metadatos seguros.

El despliegue no promoverá una revisión si la ingesta, la sonda de
disponibilidad o las consultas de aceptación fallan.

## Pruebas y evaluación

Las pruebas unitarias usarán clientes falsos alrededor del límite de Azure y
verificarán:

- selección del backend según el entorno;
- composición de consultas híbridas y filtros;
- conversión de resultados a `RetrievalHit`;
- rechazo de configuración incompleta en producción;
- comportamiento de la sonda de disponibilidad;
- sincronización determinista de documentos.

La evaluación offline seguirá usando el adaptador local para ser rápida y
reproducible. Después del despliegue se ejecutará una evaluación de aceptación
contra Azure con preguntas sobre inteligencia artificial, Terraform,
cotizaciones y preguntas fuera de alcance.

## Infraestructura y operación

El script de despliegue registrará `Microsoft.Search`, comprobará la
disponibilidad del nivel Free y creará el servicio solo cuando no implique un
costo. También configurará variables no sensibles, asignará RBAC a la identidad
administrada, ejecutará la ingesta y desplegará la nueva imagen.

La documentación mostrará comandos para repetir la ingesta, comprobar el
estado del índice y diagnosticar una falla. El README afirmará que producción
usa Azure AI Search únicamente después de que las pruebas de aceptación lo
demuestren.

## Criterios de aceptación

- El servicio Azure AI Search existe en `Enerey-Prod` con nivel Free.
- El índice contiene todos los documentos autorizados y ningún documento
  eliminado del repositorio.
- La revisión activa de Container Apps consulta Azure AI Search mediante
  identidad administrada.
- Producción no utiliza fallback local.
- `/health/ready` confirma acceso al índice.
- Las pruebas automatizadas y la evaluación offline pasan.
- Las consultas públicas de aceptación recuperan evidencia correcta y rechazan
  preguntas fuera de alcance.
- El repositorio público explica diseño, ingesta, seguridad, despliegue y
  operación sin contener secretos.
