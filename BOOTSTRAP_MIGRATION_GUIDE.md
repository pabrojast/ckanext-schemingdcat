
# Guía Post-Migración Bootstrap 5 - ckanext-schemingdcat

## ✅ Cambios Aplicados

### 1. Clases CSS Migradas
- `pull-left` → `float-start`
- `pull-right` → `float-end`
- `text-left` → `text-start`
- `text-right` → `text-end`
- `panel` → `card`
- `panel-heading` → `card-header`
- `panel-body` → `card-body`
- `btn-default` → `btn-secondary`
- `control-label` → `form-label`
- `form-group` → `mb-3`
- `help-block` → `form-text`

### 2. Atributos JavaScript Migrados
- `data-toggle` → `data-bs-toggle`
- `data-target` → `data-bs-target`
- `data-dismiss` → `data-bs-dismiss`
- `data-placement` → `data-bs-placement`
- `data-parent` → `data-bs-parent`

### 3. Estructuras Específicas
- Accordions actualizados con sintaxis Bootstrap 5
- Dropdowns con atributos data-bs-*
- Carets reemplazados por iconos Font Awesome

### 4. Archivos Creados/Modificados
- `assets/css/bootstrap5-compatibility.css` - CSS de compatibilidad
- `assets/webassets.yml` - Configuración actualizada
- Múltiples templates HTML actualizados

## 🧪 Testing Recomendado

### 1. Funcionalidad Básica
- [ ] Dropdowns se abren/cierran correctamente
- [ ] Accordions se expanden/contraen
- [ ] Botones responden al hover/click
- [ ] Formularios se ven correctos

### 2. Responsive Design
- [ ] Layout funciona en móvil
- [ ] Elementos `float-start/end` se comportan bien
- [ ] Badges y botones se adaptan

### 3. Componentes Específicos
- [ ] Descarga de formatos (CSV, JSON, etc.)
- [ ] Ejemplos de API (R, Python, cURL, JavaScript)
- [ ] Información de datasets
- [ ] Formularios de metadata

### 4. JavaScript
- [ ] Tooltips aparecen correctamente
- [ ] Modals funcionan (si los hay)
- [ ] Collapse/Expand funciona

## 🔧 Troubleshooting

### Si los dropdowns no funcionan:
1. Verificar que Bootstrap 5 JS está cargado
2. Comprobar que no hay conflictos con Bootstrap 3
3. Revisar la consola del navegador por errores

### Si el layout se ve mal:
1. Verificar que `bootstrap5-compatibility.css` se está cargando
2. Comprobar que no hay CSS conflictivo
3. Usar herramientas de desarrollo para inspeccionar estilos

### Si los accordions no funcionan:
1. Verificar atributos `data-bs-*`
2. Comprobar estructura HTML (card > card-header > card-body)
3. Verificar IDs únicos en elementos collapse

## 📝 Próximos Pasos

1. **Inmediato**: Probar funcionalidad básica
2. **Corto plazo**: Testing exhaustivo en diferentes navegadores
3. **Medio plazo**: Optimizar CSS personalizado
4. **Largo plazo**: Considerar migración completa a utilidades Bootstrap 5

## 📞 Soporte

Si encuentras problemas adicionales:
1. Revisar la consola del navegador
2. Comprobar que no quedan patrones Bootstrap 3
3. Verificar que todos los assets se están cargando
4. Usar `fix_bootstrap_migration.py` para correcciones adicionales

---
*Generado automáticamente por el verificador de migración Bootstrap 5*
