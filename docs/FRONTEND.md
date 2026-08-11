# Frontend conversacional con Flask

## Objetivo

Agregar una demostración web profesional para AIguiar AI dentro del mismo repositorio y despliegue. La interfaz permitirá explorar el perfil de Gael sin sustituir el contrato Open Responses usado por integraciones externas.

## Arquitectura

FastAPI continúa como aplicación principal y conserva `GET /health` y `POST /v1/responses`. Una aplicación Flask se monta en `/chat` mediante el adaptador WSGI de Starlette. Ambos frameworks comparten la misma instancia de `CvAgentService`; Flask no realiza una llamada HTTP al propio servidor.

Flask expone:

- `GET /chat/`: interfaz principal.
- `POST /chat/api/messages`: recibe una sola pregunta y devuelve la respuesta pública del agente.
- `GET /chat/static/*`: estilos y JavaScript versionados.

El endpoint visual aplica validación de tipo, longitud máxima, rate limiting y guardrails antes de invocar el agente. El navegador nunca recibe `OPENAI_API_KEY` ni `AGENT_API_KEY`.

## Experiencia visual

La interfaz usa el nombre **AIguiar AI** y el subtítulo **Asistente profesional**. El diseño es claro, minimalista y propio, inspirado en patrones conocidos de chat pero sin reutilizar identidad o recursos visuales de terceros.

En escritorio incluye una barra lateral con nuevo chat, búsqueda, conversaciones recientes y perfil. El área principal presenta el agente, estado, saludo, cuatro sugerencias y un composer. Durante la conversación muestra mensajes diferenciados, indicador de generación, errores recuperables y acción para copiar respuestas.

En móvil, la barra lateral se convierte en un panel activable y las sugerencias se reducen para evitar saturación. No habrá modo oscuro en esta versión.

## Estado y privacidad

Cada conversación contiene un identificador local, título derivado de la primera pregunta, fecha de actualización y mensajes. Todo se almacena en `localStorage`; el servidor recibe únicamente la pregunta actual. El usuario puede iniciar conversaciones, cambiar entre ellas, buscarlas y eliminarlas localmente.

No se implementarán cuentas, sincronización entre dispositivos, base de datos de conversaciones ni telemetría del contenido.

## Interacciones y accesibilidad

- Enter envía; Shift+Enter agrega una línea.
- Los controles sólo con icono incluyen nombre accesible.
- El estado de carga se anuncia mediante una región `aria-live`.
- El foco vuelve al composer después de recibir respuesta.
- Los targets interactivos miden al menos 44 píxeles.
- El contraste de texto cumple al menos 4.5:1.
- Las animaciones respetan `prefers-reduced-motion`.
- Los errores indican causa y acción de recuperación.

## Seguridad y errores

Se rechazan JSON inválido, contenido no JSON, preguntas vacías y entradas mayores a 8,000 caracteres. Las solicitudes sensibles usan la misma respuesta segura del endpoint Open Responses. Los errores del proveedor se convierten en mensajes públicos estables y no filtran excepciones, prompts, rutas ni configuración.

La limitación en memoria es adecuada para una demostración con una réplica; para escala horizontal se delegaría a APIM, Front Door o un almacén distribuido.

## Pruebas y aceptación

La implementación estará completa cuando:

1. `GET /chat/` entregue HTML con identidad AIguiar AI, sugerencias y controles accesibles.
2. `POST /chat/api/messages` responda con texto fundamentado usando el agente compartido.
3. Una solicitud sensible no invoque al modelo ni revele datos privados.
4. Entradas inválidas produzcan errores JSON estables.
5. Las claves no aparezcan en HTML, JavaScript ni respuestas.
6. El historial funcione exclusivamente mediante `localStorage`.
7. La UI sea utilizable a 375, 768 y 1440 píxeles sin scroll horizontal.
8. Todas las pruebas existentes, evaluación offline, build Docker y CI continúen aprobados.

## Operación

El Dockerfile copiará únicamente el paquete, conocimiento, plantillas y archivos estáticos necesarios. `/health` seguirá siendo la sonda de Azure. README y el guion de demo explicarán cómo abrir `/chat`, ejecutar pruebas y demostrar la convivencia Flask/FastAPI.
