#!/usr/bin/env python3
"""
Script de verificación post-migración Bootstrap 5
para ckanext-schemingdcat

Este script verifica que la migración se haya completado correctamente
y proporciona un reporte de estado.
"""

import os
import re
from pathlib import Path

class BootstrapMigrationVerifier:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.templates_dir = self.project_root / "ckanext" / "schemingdcat" / "templates"
        
        # Patrones que NO deberían estar presentes después de la migración
        self.legacy_patterns = {
            'CSS Classes': [
                r'\bpull-left\b',
                r'\bpull-right\b', 
                r'\btext-left\b',
                r'\btext-right\b',
                r'\bpanel\b(?!\w)',  # panel pero no panel-xxx
                r'\bpanel-default\b',
                r'\bpanel-heading\b',
                r'\bpanel-body\b',
                r'\bbtn-default\b',
                r'\bcontrol-label\b',
                r'\bform-group\b',
                r'\bhelp-block\b'
            ],
            'JavaScript Attributes': [
                r'data-toggle=',
                r'data-target=',
                r'data-dismiss=',
                r'data-placement=(?!.*data-bs-placement)'
            ]
        }
        
        # Patrones que DEBERÍAN estar presentes después de la migración
        self.new_patterns = {
            'CSS Classes': [
                r'\bfloat-start\b',
                r'\bfloat-end\b',
                r'\btext-start\b', 
                r'\btext-end\b',
                r'\bcard\b',
                r'\bcard-header\b',
                r'\bcard-body\b',
                r'\bbtn-secondary\b',
                r'\bform-label\b',
                r'\bmb-3\b',
                r'\bform-text\b'
            ],
            'JavaScript Attributes': [
                r'data-bs-toggle=',
                r'data-bs-target=',
                r'data-bs-dismiss=',
                r'data-bs-placement='
            ]
        }
    
    def find_html_files(self):
        """Encontrar todos los archivos HTML"""
        return list(self.templates_dir.rglob("*.html"))
    
    def check_file_for_patterns(self, file_path, patterns, pattern_type):
        """Verificar un archivo para patrones específicos"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            found_patterns = []
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    found_patterns.append((pattern, len(matches)))
            
            return found_patterns
        except Exception as e:
            return [('ERROR', str(e))]
    
    def verify_migration(self):
        """Verificar que la migración se completó correctamente"""
        print("🔍 Verificando migración de Bootstrap 3 a Bootstrap 5")
        print("=" * 60)
        
        html_files = self.find_html_files()
        print(f"📁 Verificando {len(html_files)} archivos HTML...")
        
        # Verificar patrones legacy (que NO deberían estar)
        print("\n🚫 Verificando patrones legacy (Bootstrap 3)...")
        legacy_issues = {}
        
        for pattern_type, patterns in self.legacy_patterns.items():
            print(f"\n  📋 Verificando {pattern_type}:")
            
            for file_path in html_files:
                found = self.check_file_for_patterns(file_path, patterns, pattern_type)
                if found:
                    if str(file_path) not in legacy_issues:
                        legacy_issues[str(file_path)] = []
                    legacy_issues[str(file_path)].extend([(pattern_type, pattern, count) for pattern, count in found])
        
        # Verificar patrones nuevos (que SÍ deberían estar)
        print("\n✅ Verificando patrones nuevos (Bootstrap 5)...")
        new_patterns_found = {}
        
        for pattern_type, patterns in self.new_patterns.items():
            print(f"\n  📋 Verificando {pattern_type}:")
            total_found = 0
            
            for file_path in html_files:
                found = self.check_file_for_patterns(file_path, patterns, pattern_type)
                if found:
                    if str(file_path) not in new_patterns_found:
                        new_patterns_found[str(file_path)] = []
                    new_patterns_found[str(file_path)].extend([(pattern_type, pattern, count) for pattern, count in found])
                    total_found += sum([count for _, count in found])
            
            print(f"    ✅ {total_found} instancias encontradas")
        
        # Reporte de resultados
        print("\n" + "=" * 60)
        print("📊 REPORTE DE VERIFICACIÓN")
        print("=" * 60)
        
        if legacy_issues:
            print("\n⚠️  PROBLEMAS ENCONTRADOS (requieren atención):")
            for file_path, issues in legacy_issues.items():
                rel_path = Path(file_path).relative_to(self.templates_dir)
                print(f"\n  📄 {rel_path}:")
                for pattern_type, pattern, count in issues:
                    print(f"    🔴 {pattern_type}: {pattern} ({count} instancias)")
        else:
            print("\n✅ No se encontraron patrones legacy de Bootstrap 3")
        
        if new_patterns_found:
            print(f"\n✅ PATRONES BOOTSTRAP 5 ENCONTRADOS:")
            total_files_with_bs5 = len(new_patterns_found)
            print(f"  📁 {total_files_with_bs5} archivos contienen patrones Bootstrap 5")
        
        # Verificar archivos específicos importantes
        print("\n🔍 VERIFICACIÓN DE ARCHIVOS CLAVE:")
        
        key_files = [
            "schemingdcat/package/read.html",
            "schemingdcat/package/snippets/download_datastore_formats.html", 
            "schemingdcat/package/snippets/download_metadata.html",
            "api_examples/r.html",
            "ajax_snippets/scd_api_info.html"
        ]
        
        for file_rel_path in key_files:
            file_path = self.templates_dir / file_rel_path
            if file_path.exists():
                has_legacy = str(file_path) in legacy_issues
                has_new = str(file_path) in new_patterns_found
                
                status = "🔴" if has_legacy else ("✅" if has_new else "⚪")
                print(f"  {status} {file_rel_path}")
            else:
                print(f"  ⚠️  {file_rel_path} (no encontrado)")
        
        # Verificar archivos de assets
        print("\n🎨 VERIFICACIÓN DE ASSETS:")
        
        css_compatibility = self.project_root / "ckanext" / "schemingdcat" / "assets" / "css" / "bootstrap5-compatibility.css"
        if css_compatibility.exists():
            print("  ✅ bootstrap5-compatibility.css creado")
        else:
            print("  🔴 bootstrap5-compatibility.css NO encontrado")
        
        webassets_file = self.project_root / "ckanext" / "schemingdcat" / "assets" / "webassets.yml"
        if webassets_file.exists():
            with open(webassets_file, 'r') as f:
                webassets_content = f.read()
            if 'bootstrap5-compatibility.css' in webassets_content:
                print("  ✅ webassets.yml incluye bootstrap5-compatibility.css")
            else:
                print("  🔴 webassets.yml NO incluye bootstrap5-compatibility.css")
        
        # Resumen final
        print("\n" + "=" * 60)
        print("📋 RESUMEN FINAL")
        print("=" * 60)
        
        if not legacy_issues:
            print("✅ MIGRACIÓN EXITOSA - No se encontraron problemas legacy")
        else:
            print(f"⚠️  MIGRACIÓN PARCIAL - {len(legacy_issues)} archivos requieren atención")
        
        print(f"\n📊 Estadísticas:")
        print(f"  📁 Archivos procesados: {len(html_files)}")
        print(f"  🔴 Archivos con problemas: {len(legacy_issues)}")
        print(f"  ✅ Archivos con Bootstrap 5: {len(new_patterns_found) if new_patterns_found else 0}")
        
        return len(legacy_issues) == 0
    
    def generate_migration_guide(self):
        """Generar guía post-migración"""
        guide_content = """
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
"""
        
        guide_path = self.project_root / "BOOTSTRAP_MIGRATION_GUIDE.md"
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide_content)
        
        print(f"📋 Guía de migración creada: {guide_path}")

def main():
    """Función principal"""
    project_root = Path(__file__).parent
    verifier = BootstrapMigrationVerifier(project_root)
    
    success = verifier.verify_migration()
    verifier.generate_migration_guide()
    
    if success:
        print("\n🎉 ¡Migración completada exitosamente!")
    else:
        print("\n⚠️  Migración requiere atención adicional.")
    
    print(f"\n📋 Consulta BOOTSTRAP_MIGRATION_GUIDE.md para más detalles.")

if __name__ == "__main__":
    main()
