---
id: heytech-apim-chatbot
title: Fachada segura para APIM y participación en chatbot empresarial
category: proyecto
evidence_level: directa
impact_type: inferido
source_kind: laboral
source: experiencia laboral confirmada y artefactos técnicos revisados
---
## Evidencia directa

Gael desarrolló una Azure Function en Java que operaba como fachada antes de
API Management. La función validaba la identidad mediante JWT, utilizaba
Managed Identity para resolver de forma protegida la configuración de
suscripción necesaria y seleccionaba el destino antes de enrutar la solicitud.
También limitaba los encabezados que podían reenviarse, con el propósito de no
propagar información sensible o innecesaria entre capas.

El alcance verificable de su autoría incluye la implementación de esta fachada,
sus pruebas y su documentación técnica. De forma separada, está confirmada su
participación dentro del equipo que trabajó en la comunicación y orquestación
de un chatbot empresarial, incluido el soporte al flujo de preparación,
validación, despliegue e integración de sus componentes de IA; esa
participación no implica atribuirle en exclusiva
el diseño o la construcción completa del chatbot.

## Impacto inferido

La fachada estableció un punto controlado para validar identidad, obtener
configuración protegida, seleccionar rutas y reducir la exposición de
encabezados. Cualitativamente, esto favoreció una integración más segura,
más fácil de probar y mantener, y comprensible para los equipos responsables
del flujo. No se atribuyen cifras de ahorro, disponibilidad o volumen porque no
hay métricas auditadas para sostenerlas.
