# Medición de uso por respuesta

## Objetivo

Mostrar debajo de cada respuesta del agente una línea compacta con el consumo
real de esa llamada y el porcentaje de presupuesto todavía disponible:

`1,234 tokens · 67.2% disponible`

La interfaz no mostrará importes monetarios, tarifas, claves ni información de
facturación.

## Alcance

- Contabilizar únicamente la llamada de generación que produjo la respuesta.
- Usar `usage.total_tokens` reportado por OpenAI, que incluye tokens de entrada
  y salida de esa respuesta.
- Inicializar el medidor con 67.2% disponible. Los valores monetarios que
  respaldan ese porcentaje permanecen exclusivamente en configuración segura.
- Calcular internamente el costo incremental con tarifas configurables por
  modelo; estos importes nunca salen en el contrato público.
- Persistir el acumulado en Azure para conservarlo entre revisiones, réplicas y
  reinicios.
- Mostrar la línea de uso en el frontend propio y exponer la misma información
  no sensible en JSON y en el evento final SSE de Open Responses.

No se intentará atribuir a una respuesta los tokens consumidos por otros
clasificadores, embeddings o procesos independientes. Tampoco se consultará ni
se expondrá el saldo de facturación de la cuenta de OpenAI.

## Arquitectura

La llamada al modelo devolverá un resultado estructurado con el texto y el uso
reportado por OpenAI. El servicio convertirá ese uso en un registro inmutable:

- `total_tokens`: entero no negativo de la respuesta actual.
- `available_percent`: decimal acotado entre 0.0 y 100.0.

Un componente `UsageBudgetStore` realizará una actualización atómica del
consumo acumulado. La implementación productiva utilizará Azure Table Storage
con control de concurrencia optimista mediante ETag; las pruebas y el entorno
local usarán una implementación en memoria con la misma interfaz. Si dos
respuestas terminan al mismo tiempo, cada costo se aplicará una sola vez.

Cada instancia de respuesta generará un identificador aleatorio interno antes
de registrar el uso. Este identificador sólo garantiza idempotencia del cargo;
no se expondrá en el pie ni permitirá que el cliente controle la contabilidad.

Las tarifas de entrada, entrada cacheada y salida serán configuración de
servidor asociada al modelo. El razonamiento está incluido por OpenAI dentro de
los tokens de salida. La fórmula interna será:

`costo = entrada × tarifa_entrada + cache × ajuste_cache + salida × tarifa_salida`

Los valores se expresarán por millón de tokens y se validarán al iniciar. El
presupuesto y consumo inicial también serán secretos/configuración operativa,
no campos controlados por el cliente.

## Flujo

1. El agente prepara evidencia y solicita una única generación final.
2. OpenAI devuelve texto y `usage` para esa llamada.
3. El servicio calcula su costo interno con las tarifas configuradas.
4. El almacén incrementa el consumo de manera atómica y devuelve el porcentaje
   actualizado.
5. El servidor agrega al texto final dos saltos de línea y, por ejemplo,
   `1,234 tokens · 67.2% disponible`; así también aparece en clientes que
   ignoran extensiones propias, incluido el portal del reto.
6. JSON y SSE incluyen además `usage.total_tokens` y la extensión segura
   `budget.available_percent`; el frontend propio reconoce el pie ya integrado
   y no lo duplica.

## Contrato y presentación

El objeto Open Responses conservará `usage.input_tokens`,
`usage.output_tokens` y `usage.total_tokens` con los valores reales. La
extensión superior `budget` contendrá únicamente:

```json
{
  "available_percent": 67.2
}
```

El endpoint Flask devolverá el mismo `usage` y `budget`. Tanto Open Responses
como Flask devolverán el texto con un único pie separado por dos saltos de
línea, para que el portal de terceros lo muestre aunque descarte los campos
adicionales. El cliente almacenará estos valores junto al mensaje para que el
historial local conserve la línea tras recargar y nunca añadirá un segundo pie.
En el frontend propio la línea tendrá estilo secundario, contraste accesible y
una etiqueta comprensible para lectores de pantalla.

## Errores y privacidad

- Si OpenAI no devuelve uso válido, la respuesta se entrega sin la línea; no se
  inventan tokens ni porcentaje.
- Si falla la persistencia, la respuesta se entrega con tokens reales pero sin
  porcentaje, se registra solamente un evento allowlisted y no se reintenta el
  cargo de forma insegura.
- El porcentaje se redondea a un decimal y se limita a `0.0..100.0`.
- Los clientes no pueden enviar ni modificar el presupuesto, el consumo o las
  tarifas.
- Logs y telemetría pueden incluir contadores agregados, pero nunca importes,
  prompts, respuestas, claves ni datos de facturación.

## Pruebas

- Extracción realista de `usage` del SDK, incluidos tokens de razonamiento.
- Ausencia segura cuando `usage` falta o es inválido.
- Cálculo de costo con entrada, cache y salida; redondeo y límites.
- Actualización atómica e idempotente ante concurrencia y reintentos.
- Paridad de `usage`, `budget` y pie visible en JSON, SSE y Flask, sin
  duplicación.
- Render exacto `1,234 tokens · 67.2% disponible`, persistencia local y
  accesibilidad.
- Regresiones que demuestren que no aparecen dólares, presupuesto, consumo,
  tarifas ni secretos en respuestas o logs.

## Operación

El despliegue creará o reutilizará una tabla dedicada y asignará a Container
Apps acceso mediante identidad administrada. Las variables no sensibles
definirán el modelo; tarifas, presupuesto y consumo inicial se cargarán como
configuración protegida. La migración inicial se ejecutará una sola vez con
67.2% disponible. Los cambios futuros de tarifa serán explícitos y versionados
para no recalcular retroactivamente respuestas ya contabilizadas.
