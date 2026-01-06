# MODULUS - Environment Configuration
# Last Updated: 2025-01-06

## ENTORNO DE DESARROLLO

El desarrollo de MODULUS se realiza en el **ordenador local del desarrollador**.

### ⚠️ IMPORTANTE PARA EL LLM (Claude)

El entorno de Claude es un **contenedor aislado SIN acceso a internet**.
Las librerías pueden NO estar instaladas en el contenedor de Claude, pero **SÍ están instaladas en el proyecto local del desarrollador**.

### REGLAS PARA EL LLM:

1. **ASUMIR que todas las librerías están instaladas** en el ordenador local
2. **NO degradar el código** por falta de librerías en el contenedor de Claude
3. **USAR siempre la mejor solución técnica** (Pydantic, numpy, etc.)
4. Si necesitas una librería nueva que NO esté en la lista de abajo, **PEDIR al usuario que la instale**
5. El usuario instalará la librería en su entorno local y confirmará

### Librerías instaladas en el proyecto local:

| Paquete | Versión | Uso |
|---------|---------|-----|
| numpy | 2.x | Arrays y cálculo numérico |
| scipy | 1.x | Integración ODE, optimización |
| pandas | 2.x | Manipulación de datos |
| pydantic | 2.x | Validación de contratos |
| pytest | 9.x | Testing |
| flake8 | 6.x | Linting |
| mypy | 1.x | Type checking |
| black | 23.x | Formateo de código |
| fastapi | 0.100+ | API REST |
| uvicorn | 0.22+ | Servidor ASGI |
| matplotlib | 3.x | Gráficos |
| reportlab | 4.x | Generación de PDFs |

### Si necesitas una librería nueva:

```
LLM: "Necesito instalar la librería X para implementar Y. 
      ¿Puedes ejecutar: pip install X?"

Usuario: [instala en su entorno local]
Usuario: "Listo, instalado"

LLM: [continúa con el desarrollo]
```

---

## VERIFICACIÓN DEL ENTORNO LOCAL

El desarrollador puede verificar su entorno ejecutando:

```bash
make check
```

Para verificar librerías específicas:

```bash
python3 -c "import pydantic; print(f'pydantic: {pydantic.__version__}')"
python3 -c "import numpy; print(f'numpy: {numpy.__version__}')"
python3 -c "import pytest; print(f'pytest: {pytest.__version__}')"
```

---

## FLUJO DE TRABAJO

1. **Claude genera código** usando las mejores librerías disponibles
2. **Usuario copia código** a su proyecto local
3. **Usuario ejecuta `make check`** en su terminal
4. **Si hay errores**, usuario reporta a Claude
5. **Claude ajusta** y genera nuevo código

El código SIEMPRE se ejecuta en el **ordenador local del usuario**, NUNCA en el contenedor de Claude.
