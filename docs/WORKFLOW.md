# MODULUS — Workflow Instructions for LLM
# Last Updated: 2025-01-06
#
# ⚠️  INSTRUCCIONES OBLIGATORIAS PARA EL LLM
# ⚠️  LEER ANTES DE CADA SESIÓN

## REGLA 1: ENTREGA DE ARCHIVOS

Cuando generes archivos nuevos o modificados para el proyecto:

1. **SIEMPRE** proporciona el comando para mover/copiar al proyecto local
2. El comando debe ser **copy-paste ready** para la terminal del usuario
3. Formato estándar:

```bash
cp ~/Downloads/ARCHIVO tests/ruta/destino/ && python3 -m pytest tests/ruta/ -v
```

**Ejemplos:**

```bash
# Un archivo
cp ~/Downloads/test_example.py tests/unit/ && python3 -m pytest tests/unit/test_example.py -v

# Múltiples archivos
cp ~/Downloads/file1.py ~/Downloads/file2.py src/core/module/ && python3 -m pytest tests/ -v

# Reemplazar archivo existente
cp ~/Downloads/STATE.md docs/ && cat docs/STATE.md | head -20
```

---

## REGLA 2: FIN DE FASE

Cuando se **completa una FASE** (no sesión, FASE completa):

1. **AUTOMÁTICAMENTE** generar `STATE.md` actualizado
2. Incluir el comando para copiarlo:

```bash
cp ~/Downloads/STATE.md docs/
```

3. Incluir comando de commit sugerido:

```bash
git add -A && git commit -m "✅ FASE X completa: [descripción]"
```

---

## REGLA 3: FIN DE SESIÓN

Al terminar cada **sesión** (no fase):

1. Proporcionar resumen de cambios
2. Listar archivos creados/modificados
3. Comando para mover archivos
4. Comando para ejecutar tests relevantes
5. Indicar qué actualizar en STATE.md (o proporcionar el archivo si es fin de fase)

---

## REGLA 4: ESTRUCTURA DE COMANDOS

El usuario está en macOS. Comandos deben ser compatibles con zsh/bash.

**Directorio de descargas:** `~/Downloads/`
**Directorio del proyecto:** El usuario está en la raíz del proyecto cuando ejecuta comandos

**Patrón estándar:**
```bash
# Copiar archivo(s) + ejecutar tests
cp ~/Downloads/ARCHIVO DESTINO/ && python3 -m pytest TESTS -v

# Solo copiar
cp ~/Downloads/ARCHIVO DESTINO/

# Verificar todo
make check
```

---

## REGLA 5: FORMATO DE RESPUESTA AL ENTREGAR ARCHIVOS

```
## Archivos generados

| Archivo | Destino | Acción |
|---------|---------|--------|
| `file.py` | `src/core/module/` | Nuevo |
| `test_file.py` | `tests/unit/` | Nuevo |

## Comando para instalar

\`\`\`bash
cp ~/Downloads/file.py src/core/module/ && cp ~/Downloads/test_file.py tests/unit/ && python3 -m pytest tests/unit/test_file.py -v
\`\`\`

## Verificar todo

\`\`\`bash
make check
\`\`\`
```

---

## CHECKLIST ANTES DE RESPONDER

- [ ] ¿He leído STATE.md para saber el estado actual?
- [ ] ¿Estoy en la sesión correcta del ROADMAP?
- [ ] ¿Los archivos que genero van con comando de instalación?
- [ ] ¿Si es fin de FASE, incluyo STATE.md actualizado?
- [ ] ¿El comando es copy-paste ready?
