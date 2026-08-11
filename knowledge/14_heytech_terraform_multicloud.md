---
id: heytech-terraform-multicloud
title: Conectividad multicloud Site-to-Site entre Azure, AWS y GCP
category: proyecto
evidence_level: directa
impact_type: inferido
source_kind: laboral
source: experiencia laboral confirmada y artefactos de infraestructura revisados
---
## Evidencia directa

Gael reutilizó módulos existentes de infraestructura como código del entorno
Azure como base para trabajar en conectividad Site-to-Site entre Azure y AWS, y
entre Azure y GCP. Su labor se concentró en el diseño y configuración de
gateways, sesiones BGP y rutas para comunicar las redes de cada proveedor.

La solución separaba la configuración por ambientes. Gael revisó las
dependencias entre gateways y tablas de rutas, validó los despliegues y comprobó
la conectividad entre los extremos para identificar problemas por capa.

## Impacto inferido

Las conexiones multicloud establecieron rutas explícitas y verificables entre
los proveedores. La separación por ambientes y la validación por capas ayudaron
a localizar fallas de conectividad sin atribuir cifras de costo, tiempo o
incidentes que no cuentan con métricas auditadas.
