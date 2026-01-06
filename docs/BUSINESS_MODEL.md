# MODULUS — Business Model & Vision
# Version: 1.0
# Last Updated: 2025-01-04
#
# Este documento define la visión de negocio que guía todas las decisiones técnicas.
# El producto técnico existe para servir este modelo de negocio.
# ============================================================================

## VISIÓN EN UNA FRASE

**MODULUS es el "Decision & Compliance OS" de la industria de suplementos y nutrición funcional.**

No vendemos simulaciones. Vendemos **reducción de riesgo**, **aceleración de lanzamientos**, y **trazabilidad auditable**.

---

## EL PROBLEMA QUE RESOLVEMOS

### Para el Director de I+D:
```
"Voy a invertir €200k en fabricar este producto. 
¿Funcionará? ¿Tendrá efectos secundarios? ¿Puedo defender los claims?"

HOY: Intuición + prueba y error + ensayos caros
CON MODULUS: Respuesta en 48h con evidencia trazable
```

### Para el Director de Regulatory/Legal:
```
"¿Puedo poner 'Sustained Energy' en el packaging sin que me demanden?"

HOY: Opiniones de abogados + dedos cruzados
CON MODULUS: "73% de la población muestra efecto >4h. Claim defendible con nivel de confianza X"
```

### Para el CEO:
```
"¿Este producto va a generar malas reviews por insomnio o ansiedad?"

HOY: Lo descubres después de lanzar
CON MODULUS: "23% de metabolizadores lentos de cafeína tendrán problemas de sueño. 
             Recomendación: añadir warning o reformular"
```

---

## MODELO DE NEGOCIO: 3 FASES DE EVOLUCIÓN

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  AÑO 1: "DECISION PACK" (Services + Software)                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                         │
│  • Vender packs de análisis a marcas                                   │
│  • Output: PDF + Evidence Bundle                                        │
│  • Pricing: €50k - €250k por proyecto                                  │
│  • Target: 10-20 clientes                                              │
│  • Revenue: €500k - €2M                                                │
│                                                                         │
│  OBJETIVO: Validar producto, generar cash flow, aprender del mercado   │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  AÑO 2: "POWERED BY MODULUS" (Platform + Data)                         │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                         │
│  • Consumer web app marca blanca                                        │
│  • QR en packaging → personalización en tiempo real                    │
│  • Pricing: €100k/año + €0.10-0.20/unidad                              │
│  • Target: 5-10 partners estratégicos                                  │
│  • Revenue: €2M - €5M                                                  │
│                                                                         │
│  OBJETIVO: Obtener datos reales de consumidores, crear moat            │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  AÑO 3+: "MODULUS STANDARD" (Certification + Data Monopoly)            │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━             │
│  • "Modulus-Verified" como sello de industria                          │
│  • Base de datos propietaria de outcomes reales                        │
│  • Venta de insights agregados                                         │
│  • Posible: Risk underwriting / garantías                              │
│  • Revenue: €10M+                                                      │
│                                                                         │
│  OBJETIVO: Posición de estándar de industria, moat imposible de copiar │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## PAQUETES COMERCIALES (AÑO 1)

### PACK 1: "Protocol Assessment" — €50k

**PARA:** Marcas que quieren validar UN producto antes de lanzar

**INCLUYE:**
- Simulación 24h del producto en 1,000 gemelos digitales
- Decision Page (Go / Caution / No-Go)
- Top 5 riesgos identificados
- Risk Map por 3 segmentos (BMI, edad, sensibilidad cafeína)
- Recomendaciones de timing y dosificación
- PDF profesional (20 páginas)
- Evidence summary (fuentes principales)

**ENTREGA:** 2 semanas

**INPUT REQUERIDO:** Fórmula completa, target demográfico

**FEATURES TÉCNICAS NECESARIAS:**
- [x] 24h Timeline Engine
- [x] 15+ ingredientes modelados
- [x] Population simulation (N=1000)
- [x] Decision Page generator
- [x] Basic Risk Map
- [x] PDF generator v1

---

### PACK 2: "Enterprise Risk & Compliance" — €150-250k

**PARA:** Multi-brand groups, CDMOs, retailers con múltiples SKUs

**INCLUYE (todo del Pack 1, más):**
- Hasta 5 productos/SKUs evaluados
- Simulación en 10,000 gemelos digitales
- Risk Map completo (6 segmentos)
- Label & Timing Recommendations (texto sugerido para packaging)
- "Modulus Protocol Certificate" (sello verificado)
- Evidence Bundle completo (50+ referencias con DOIs)
- Reproducibility Package (JSON + hash + versión)
- Comparativa entre productos (A vs B vs C)
- 2 rondas de optimización ("¿y si cambiamos X?")

**ENTREGA:** 4-6 semanas

**ADD-ONS DISPONIBLES:**
- Producto adicional: +€40k
- Integración con datos internos (devoluciones, reviews): +€50k
- Workshop presencial con equipo: +€15k

**FEATURES TÉCNICAS NECESARIAS:**
- Todo de Pack 1, más:
- [x] Population simulation (N=10000)
- [x] 6-segment Risk Map
- [x] A/B/C comparison engine
- [x] Evidence Registry completo
- [x] Reproducibility Bundle
- [x] Certificate generator
- [x] Optimization suggestions
- [x] PDF generator v2 (40+ páginas)

---

### PACK 3: "Strategic Partnership + Powered By" — €250-500k/año

**PARA:** Marcas grandes que quieren diferenciación en mercado

**INCLUYE (todo del Pack 2, más):**
- Productos ilimitados
- "Powered by Modulus" consumer web app (marca blanca)
- QR/Link único para cada SKU
- Dashboard de analytics de uso de consumidores
- Datos de comportamiento agregados
- Actualizaciones trimestrales del modelo
- Acceso prioritario a nuevos ingredientes/features
- Co-desarrollo de claims específicos

**PRICING OPTIONS:**
- Opción A: €100k/año base + €0.10-0.20 por unidad con QR escaneado
- Opción B: €250-500k/año flat (todo incluido)

**ENTREGA:** Setup 8 semanas, luego servicio continuo

**FEATURES TÉCNICAS NECESARIAS:**
- Todo de Pack 2, más:
- [ ] Consumer Web App (responsive, marca blanca)
- [ ] Real-time personalization API (<100ms)
- [ ] QR/Link management system
- [ ] Consumer analytics dashboard
- [ ] Data ingestion pipeline (outcomes reales)

---

## TARGET CUSTOMERS (PRIORIDAD)

### Tier 1: CDMOs (Contract Development & Manufacturing)
```
POR QUÉ SON IDEALES:
- Formulan para MUCHAS marcas (1 cliente = muchos productos)
- Tienen presupuesto (€100k-500k es pequeño para ellos)
- Pueden imponer tu sistema a sus clientes
- Distribución orgánica

EJEMPLOS: Catalent, Lonza, Capsugel, fabricantes regionales

APPROACH: "Ofrezco a tus clientes un valor añadido que te diferencia"
```

### Tier 2: Multi-Brand Supplement Groups
```
POR QUÉ SON BUENOS:
- Múltiples marcas = múltiples productos = alto ticket
- Decisiones centralizadas (un procurement)
- Buscan estandarización

EJEMPLOS: Glanbia (Optimum Nutrition), Iovate (MuscleTech), grupos de private equity con portfolios de marcas

APPROACH: "Estandariza el proceso de lanzamiento en todo tu portfolio"
```

### Tier 3: Functional Food Companies
```
POR QUÉ SON BUENOS:
- Compliance más estricto que suplementos
- Presupuestos más grandes
- Valoran evidencia científica

EJEMPLOS: Nestlé Health Science, Abbott Nutrition, Danone

APPROACH: "Evidence-based development que tu equipo regulatorio va a amar"
```

### Tier 4: Retailers/Marketplaces
```
POR QUÉ SON INTERESANTES:
- Problema de devoluciones/reviews negativos
- Quieren filtrar productos malos
- Alto volumen

EJEMPLOS: Amazon (supplements category), iHerb, grandes farmacias

APPROACH: "Reduce devoluciones y malas reviews con pre-screening"
```

---

## EL MOAT (VENTAJA COMPETITIVA DEFENDIBLE)

### Año 1: Moat Débil (Ejecución)
```
- Modelos bien implementados (copiable con esfuerzo)
- Expertise en PK/PD de suplementos (copiable)
- Primeros clientes y casos de estudio (algo de ventaja)
```

### Año 2: Moat Medio (Datos + Reputación)
```
- Base de datos de fórmulas evaluadas (propietario)
- Datos de outcomes reales de consumidores (único)
- Reputación como "el estándar" (intangible pero valioso)
- "Modulus-Verified" empezando a ser reconocido
```

### Año 3+: Moat Fuerte (Network Effects + Data)
```
- Imposible de copiar:
  * Dataset de outcomes más grande del mundo
  * Modelos calibrados con datos reales (no solo literatura)
  * Posición de "estándar de industria"
  * Clientes que dependen de ti para compliance

- Competidor nuevo tendría que:
  * Construir modelos (1 año)
  * Conseguir clientes (2 años)
  * Acumular datos (3+ años)
  * = Siempre estarán 4 años detrás
```

---

## FLYWHEEL DE DATOS

```
                         ┌───────────────────────┐
                         │   Cliente compra      │
                         │   Pack 1/2/3          │
                         └───────────┬───────────┘
                                     │
                                     ▼
              ┌──────────────────────────────────────────┐
              │  MODULUS recibe:                         │
              │  • Fórmula del producto                  │
              │  • Target demográfico                    │
              │  • (Pack 2+) Datos históricos            │
              │  • (Pack 3) Outcomes reales consumidores │
              └──────────────────────┬───────────────────┘
                                     │
                                     ▼
              ┌──────────────────────────────────────────┐
              │  Dataset crece:                          │
              │  • Más fórmulas → mejor librería         │
              │  • Más outcomes → mejor calibración      │
              │  • Más segmentos → mejores risk maps     │
              └──────────────────────┬───────────────────┘
                                     │
                                     ▼
              ┌──────────────────────────────────────────┐
              │  Modelo mejora:                          │
              │  • Predicciones más precisas             │
              │  • Nuevas interacciones descubiertas     │
              │  • Confianza más alta en claims          │
              └──────────────────────┬───────────────────┘
                                     │
                                     ▼
              ┌──────────────────────────────────────────┐
              │  Más valor para clientes:                │
              │  • Mejores resultados                    │
              │  • Más dispuestos a pagar                │
              │  • Refieren a otros                      │
              └──────────────────────┬───────────────────┘
                                     │
                                     └────────────────────┐
                                                          │
                         ┌────────────────────────────────┘
                         │
                         ▼
                    (Ciclo se repite)
```

---

## MÉTRICAS DE ÉXITO

### Año 1
| Métrica | Target |
|---------|--------|
| Clientes Pack 1 | 5-10 |
| Clientes Pack 2 | 2-3 |
| Revenue | €500k-1M |
| NPS | >50 |

### Año 2
| Métrica | Target |
|---------|--------|
| Clientes total | 20-30 |
| Clientes Pack 3 | 3-5 |
| Revenue | €2-3M |
| Datos de consumidores | 100k+ datapoints |
| "Modulus-Verified" productos | 50+ |

### Año 3+
| Métrica | Target |
|---------|--------|
| Revenue | €5-10M |
| Margen | >70% |
| Datos de outcomes | 1M+ datapoints |
| Posición mercado | Top 3 en categoría |

---

## DECISIONES DE NEGOCIO QUE AFECTAN EL PRODUCTO

### 1. PDF es el producto (no el software)
```
IMPLICACIÓN TÉCNICA:
- PDF generator es crítico, no un "nice to have"
- Cada feature debe preguntarse: "¿Cómo aparece en el PDF?"
- El PDF debe ser "de procurement" (entendible sin explicación)
```

### 2. Evidence es first-class citizen
```
IMPLICACIÓN TÉCNICA:
- Cada parámetro debe tener source + confidence
- Evidence Registry no es opcional
- El cliente de €200k preguntará "¿en qué se basa este número?"
```

### 3. Reproducibility es requisito
```
IMPLICACIÓN TÉCNICA:
- Mismo input = mismo output, SIEMPRE
- Hash + versión + seed en cada resultado
- Poder regenerar un reporte de hace 6 meses exactamente igual
```

### 4. Datos de outcomes son el moat largo plazo
```
IMPLICACIÓN TÉCNICA:
- Diseñar para ingesta de datos desde el principio
- Aunque sea CSV manual al inicio
- Estructura que permita escalar a real-time después
```

---

## RIESGOS Y MITIGACIONES

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Nadie paga €50k+ | Media | Alto | Validar con 5 conversaciones antes de construir features |
| Modelos no son suficientemente precisos | Media | Alto | Comunicar incertidumbre, no prometer más de lo que podemos |
| Competidor bien financiado | Baja | Medio | Acelerar flywheel de datos, construir relaciones |
| Regulación cambia | Baja | Medio | Ser conservador en claims, no prometer "EFSA approval" |
| Dependencia de un cliente grande | Media | Medio | Diversificar, no más de 30% revenue de un cliente |

---

## ALINEAMIENTO PRODUCTO-NEGOCIO

| Feature Técnica | Pack 1 | Pack 2 | Pack 3 | Prioridad |
|-----------------|--------|--------|--------|-----------|
| 24h Timeline Engine | ✅ | ✅ | ✅ | P0 |
| 15 ingredientes | ✅ | ✅ | ✅ | P0 |
| Population (N=1000) | ✅ | ✅ | ✅ | P0 |
| Decision Page | ✅ | ✅ | ✅ | P0 |
| Basic Risk Map | ✅ | ✅ | ✅ | P0 |
| PDF v1 | ✅ | ✅ | ✅ | P0 |
| Population (N=10000) | | ✅ | ✅ | P1 |
| Full Risk Map (6 seg) | | ✅ | ✅ | P1 |
| Evidence Bundle | | ✅ | ✅ | P1 |
| Certificate | | ✅ | ✅ | P1 |
| A/B Comparison | | ✅ | ✅ | P1 |
| PDF v2 (40+ pág) | | ✅ | ✅ | P1 |
| Consumer Web App | | | ✅ | P2 |
| Real-time API | | | ✅ | P2 |
| Analytics Dashboard | | | ✅ | P2 |
| Data Ingestion | | | ✅ | P2 |

**P0 = Pack 1 vendible (€50k)**
**P1 = Pack 2 vendible (€150-250k)**
**P2 = Pack 3 vendible (€250-500k/año)**
