# MODULUS — Architecture Decision Log
# 
# Este documento registra decisiones importantes y su justificación.
# Útil para entender "por qué" cuando se revisa código meses después.

## ADR-001: Inmutabilidad del Estado Fisiológico

**Fecha:** 2025-01-04
**Estado:** Aceptado

**Contexto:**
Necesitamos representar el estado del cuerpo en cada momento. Podríamos usar objetos mutables (más rápido) o inmutables (más seguro).

**Decisión:**
PhysiologicalState es un frozen dataclass. Cada step() crea un NUEVO estado.

**Justificación:**
- Reproducibilidad: El mismo input siempre da el mismo output
- Debugging: Puedo inspeccionar cualquier estado pasado
- Paralelización: Sin race conditions
- El costo de crear objetos es mínimo vs. los bugs que evita

**Consecuencias:**
- Ligero overhead de memoria (muchos objetos)
- Código más verboso (siempre crear nuevo estado)

---

## ADR-002: Separación Timeline vs State vs Models

**Fecha:** 2025-01-04
**Estado:** Aceptado

**Contexto:**
Podríamos tener los modelos fisiológicos manejando directamente los eventos, o separar en capas.

**Decisión:**
Tres capas separadas:
1. Timeline: Solo maneja eventos y tiempos
2. State: Solo representa el estado actual
3. Models: Solo calculan cambios dado un estado

**Justificación:**
- Single Responsibility: Cada capa hace una cosa
- Testabilidad: Puedo testear cada capa independientemente
- Flexibilidad: Puedo cambiar un modelo sin tocar el timeline
- Los contratos entre capas son claros

**Consecuencias:**
- Más archivos y clases
- Necesita documentación de contratos
- Curva de aprendizaje para nuevos developers

---

## ADR-003: Librería de Ingredientes en JSON

**Fecha:** 2025-01-04
**Estado:** Aceptado

**Contexto:**
Los parámetros PK/PD de ingredientes podrían estar hardcodeados, en base de datos SQL, o en JSON.

**Decisión:**
JSON file en data/reference/ingredients.json

**Justificación:**
- Versionable en git (podemos ver historial de cambios)
- Fácil de editar manualmente
- No requiere base de datos
- Puede migrarse a DB después si es necesario
- LLM puede generar/editar JSON fácilmente

**Consecuencias:**
- No hay queries complejas (pero no las necesitamos)
- Hay que cargar todo en memoria (pero son ~50 ingredientes)
- Validación manual del schema

---

## ADR-004: Contratos Como Tests

**Fecha:** 2025-01-04
**Estado:** Aceptado

**Contexto:**
Los contratos entre módulos podrían ser solo documentación o también tests ejecutables.

**Decisión:**
Cada contrato en CONTRACTS.md tiene un test correspondiente en test_contracts.py

**Justificación:**
- Documentación que no se valida se desactualiza
- Tests que fallan = sabes inmediatamente si rompiste algo
- Sirve como especificación ejecutable

**Consecuencias:**
- Más tests que mantener
- Hay que actualizar tests cuando cambian contratos

---

## ADR-005: Streaming Aggregation para Poblaciones

**Fecha:** 2025-01-04
**Estado:** Aceptado (heredado de v1)

**Contexto:**
Simular 10,000 personas genera muchos datos. Podríamos guardar todo o agregar on-the-fly.

**Decisión:**
StreamingAggregator procesa cada resultado y lo descarta. Solo mantiene estadísticas.

**Justificación:**
- Memoria O(1) por individuo vs O(N)
- Permite escalar a N muy grande
- Las métricas agregadas son lo que importa para el negocio

**Consecuencias:**
- No podemos hacer drill-down a individuo específico (a menos que lo guardemos explícitamente)
- Welford's algorithm para varianza online

---

## ADR-006: Evidence-Based Parameters

**Fecha:** 2025-01-04
**Estado:** Aceptado

**Contexto:**
Los parámetros PK/PD podrían venir de cualquier fuente o estar documentados rigurosamente.

**Decisión:**
CADA parámetro debe tener:
- Valor numérico
- Fuente (paper DOI o base de datos)
- Nivel de confianza (high/medium/low/theoretical)

**Justificación:**
- Credibilidad ante clientes (especialmente pharma)
- Reproducibilidad científica
- Podemos defender nuestras predicciones
- Es lo que justifica €200k+ de precio

**Consecuencias:**
- Más trabajo al añadir ingredientes
- Necesitamos revisar literatura
- Algunos parámetros tendrán que ser "estimated"

---

## ADR-007: 24h como Unidad de Simulación

**Fecha:** 2025-01-04
**Estado:** Aceptado

**Contexto:**
Podríamos simular cualquier duración (1h, 8h, 24h, 7 días).

**Decisión:**
La unidad base es 24h (un día completo).

**Justificación:**
- Un día es la unidad natural de uso de suplementos
- Captura ciclo circadiano
- Captura interacción con comidas
- Captura impacto en sueño
- Es lo que el cliente quiere saber

**Consecuencias:**
- Más puntos de tiempo (1440 con dt=1min)
- Necesitamos modelar ritmo circadiano (cortisol al menos)
- Simulación más larga que v1

---

## TEMPLATE PARA NUEVAS DECISIONES

```
## ADR-XXX: [Título]

**Fecha:** YYYY-MM-DD
**Estado:** Propuesto | Aceptado | Rechazado | Deprecado

**Contexto:**
[Situación que requiere decisión]

**Decisión:**
[Qué decidimos hacer]

**Justificación:**
[Por qué esta opción y no otras]

**Consecuencias:**
[Qué implica esta decisión]
```
