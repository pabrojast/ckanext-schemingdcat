#!/usr/bin/env python3
"""
Script de corrección para completar la migración de Bootstrap 3 a Bootstrap 5
en ckanext-schemingdcat

Este script corrige los problemas restantes después de la migración inicial.
"""

import os
import re
import shutil
import glob
from pathlib import Path

class BootstrapMigrationFixer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.templates_dir = self.project_root / "ckanext" / "schemingdcat" / "templates"
        self.backup_dir = self.project_root / "bootstrap_migration_fix_backup"
        
        # Mapeo de clases Bootstrap 3 -> Bootstrap 5 que faltaron
        self.missing_class_mappings = {
            # Sistema de Grid y posicionamiento
            r'\bpull-left\b': 'float-start',
            r'\bpull-right\b': 'float-end',
            r'\btext-left\b': 'text-start',
            r'\btext-right\b': 'text-end',
            
            # Paneles -> Cards
            r'\bpanel\b': 'card',
            r'\bpanel-default\b': 'card',
            r'\bpanel-heading\b': 'card-header',
            r'\bpanel-body\b': 'card-body',
            r'\bpanel-footer\b': 'card-footer',
            r'\bpanel-title\b': 'card-title',
            r'\bpanel-collapse\b': 'collapse',
            
            # Botones
            r'\bbtn-default\b': 'btn-secondary',
            
            # Formularios
            r'\bcontrol-label\b': 'form-label',
            r'\bform-group\b': 'mb-3',
            r'\bhelp-block\b': 'form-text',
            
            # Navegación
            r'\bnavbar-default\b': 'navbar-light bg-light',
            r'\bnavbar-inverse\b': 'navbar-dark bg-dark',
            
            # Accordion
            r'\baccordion-toggle\b': 'accordion-button',
        }
        
        # Atributos JavaScript Bootstrap 3 -> Bootstrap 5
        self.js_attributes_mapping = {
            # Eliminar atributos duplicados y corregir
            r'data-toggle="dropdown"[^>]*data-bs-toggle="dropdown"': 'data-bs-toggle="dropdown"',
            r'data-bs-toggle="dropdown"[^>]*data-toggle="dropdown"': 'data-bs-toggle="dropdown"',
            r'data-toggle="collapse"[^>]*data-bs-toggle="collapse"': 'data-bs-toggle="collapse"',
            r'data-bs-toggle="collapse"[^>]*data-toggle="collapse"': 'data-bs-toggle="collapse"',
            r'data-toggle="tooltip"[^>]*data-bs-toggle="tooltip"': 'data-bs-toggle="tooltip"',
            r'data-bs-toggle="tooltip"[^>]*data-toggle="tooltip"': 'data-bs-toggle="tooltip"',
            
            # Corregir atributos individuales
            r'data-toggle="modal"': 'data-bs-toggle="modal"',
            r'data-toggle="dropdown"': 'data-bs-toggle="dropdown"',
            r'data-toggle="collapse"': 'data-bs-toggle="collapse"',
            r'data-toggle="tooltip"': 'data-bs-toggle="tooltip"',
            r'data-target="([^"]*)"': r'data-bs-target="\1"',
            r'data-dismiss="modal"': 'data-bs-dismiss="modal"',
            r'data-dismiss="alert"': 'data-bs-dismiss="alert"',
            r'data-placement="([^"]*)"': r'data-bs-placement="\1"',
        }
    
    def create_backup(self):
        """Crear backup antes de aplicar correcciones"""
        print("🔄 Creando backup antes de aplicar correcciones...")
        
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        
        shutil.copytree(self.templates_dir, self.backup_dir)
        print(f"✅ Backup creado en: {self.backup_dir}")
    
    def find_html_files(self):
        """Encontrar todos los archivos HTML en el directorio de templates"""
        return list(self.templates_dir.rglob("*.html"))
    
    def fix_css_classes(self, content):
        """Corregir clases CSS que no se migraron correctamente"""
        updated_content = content
        changes_made = []
        
        for old_pattern, new_class in self.missing_class_mappings.items():
            # Buscar clases dentro de atributos class
            class_pattern = rf'class="([^"]*){old_pattern}([^"]*)"'
            matches = list(re.finditer(class_pattern, updated_content))
            
            if matches:
                for match in reversed(matches):
                    old_class_attr = match.group(0)
                    before_class = match.group(1)
                    after_class = match.group(2)
                    
                    # Crear la nueva clase
                    new_class_attr = f'class="{before_class}{new_class}{after_class}"'
                    
                    # Reemplazar en el contenido
                    start, end = match.span()
                    updated_content = updated_content[:start] + new_class_attr + updated_content[end:]
                    
                    if old_pattern not in [change for change in changes_made]:
                        changes_made.append(f"{old_pattern} → {new_class}")
        
        return updated_content, changes_made
    
    def fix_js_attributes(self, content):
        """Corregir atributos JavaScript duplicados y sin migrar"""
        updated_content = content
        changes_made = []
        
        for old_pattern, new_attr in self.js_attributes_mapping.items():
            if re.search(old_pattern, updated_content):
                updated_content = re.sub(old_pattern, new_attr, updated_content)
                changes_made.append(f"Fixed: {old_pattern}")
        
        return updated_content, changes_made
    
    def fix_accordion_structure(self, content):
        """Corregir estructuras de accordion para Bootstrap 5"""
        updated_content = content
        changes_made = []
        
        # Buscar patrones de accordion y corregirlos
        accordion_patterns = [
            # Cambiar data-parent por data-bs-parent
            (r'data-parent="([^"]*)"', r'data-bs-parent="\1"'),
            
            # Corregir href="#collapse-" por data-bs-target="#collapse-"
            (r'href="#collapse-([^"]*)"', r'data-bs-target="#collapse-\1"'),
        ]
        
        for old_pattern, new_pattern in accordion_patterns:
            if re.search(old_pattern, updated_content):
                updated_content = re.sub(old_pattern, new_pattern, updated_content)
                changes_made.append(f"Accordion: {old_pattern} → {new_pattern}")
        
        return updated_content, changes_made
    
    def fix_dropdown_structure(self, content):
        """Corregir estructuras de dropdown para Bootstrap 5"""
        updated_content = content
        changes_made = []
        
        # Buscar dropdowns y asegurar que tengan la clase correcta
        dropdown_patterns = [
            # Asegurar que los dropdown-menu tengan la clase correcta
            (r'class="dropdown-menu"', 'class="dropdown-menu"'),
            
            # Cambiar dropdown-toggle por dropdown-toggle correcto
            (r'dropdown-toggle"([^>]*?)data-bs-toggle="dropdown"', r'dropdown-toggle"\1data-bs-toggle="dropdown"'),
        ]
        
        for old_pattern, new_pattern in dropdown_patterns:
            if re.search(old_pattern, updated_content):
                updated_content = re.sub(old_pattern, new_pattern, updated_content)
                changes_made.append(f"Dropdown: {old_pattern}")
        
        return updated_content, changes_made
    
    def remove_duplicate_attributes(self, content):
        """Eliminar atributos duplicados como data-toggle y data-bs-toggle en el mismo elemento"""
        updated_content = content
        changes_made = []
        
        # Patrones para encontrar elementos con atributos duplicados
        duplicate_patterns = [
            # data-toggle y data-bs-toggle en el mismo elemento
            (r'(\S+)(\s+[^>]*?)data-toggle="([^"]*)"([^>]*?)data-bs-toggle="\3"', r'\1\2data-bs-toggle="\3"\4'),
            (r'(\S+)(\s+[^>]*?)data-bs-toggle="([^"]*)"([^>]*?)data-toggle="\3"', r'\1\2data-bs-toggle="\3"\4'),
            
            # data-target y data-bs-target en el mismo elemento
            (r'(\S+)(\s+[^>]*?)data-target="([^"]*)"([^>]*?)data-bs-target="\3"', r'\1\2data-bs-target="\3"\4'),
            (r'(\S+)(\s+[^>]*?)data-bs-target="([^"]*)"([^>]*?)data-target="\3"', r'\1\2data-bs-target="\3"\4'),
        ]
        
        for old_pattern, new_pattern in duplicate_patterns:
            if re.search(old_pattern, updated_content):
                updated_content = re.sub(old_pattern, new_pattern, updated_content)
                changes_made.append(f"Removed duplicates: {old_pattern}")
        
        return updated_content, changes_made
    
    def process_file(self, file_path):
        """Procesar un archivo HTML individual"""
        print(f"🔍 Procesando: {file_path}")
        
        all_changes = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Aplicar todas las correcciones
            content, css_changes = self.fix_css_classes(content)
            if css_changes:
                all_changes.extend(css_changes)
            
            content, js_changes = self.fix_js_attributes(content)
            if js_changes:
                all_changes.extend(js_changes)
            
            content, accordion_changes = self.fix_accordion_structure(content)
            if accordion_changes:
                all_changes.extend(accordion_changes)
            
            content, dropdown_changes = self.fix_dropdown_structure(content)
            if dropdown_changes:
                all_changes.extend(dropdown_changes)
            
            content, duplicate_changes = self.remove_duplicate_attributes(content)
            if duplicate_changes:
                all_changes.extend(duplicate_changes)
            
            # Solo escribir si hay cambios
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✅ Archivo corregido: {file_path}")
                for change in all_changes:
                    print(f"     - {change}")
                return True
            else:
                print(f"  ⚪ Sin cambios necesarios: {file_path}")
                return False
                
        except Exception as e:
            print(f"  ❌ Error procesando {file_path}: {e}")
            return False
    
    def run_fix(self):
        """Ejecutar todas las correcciones"""
        print("🔧 Iniciando correcciones de migración Bootstrap 5")
        print("=" * 60)
        
        # Crear backup
        self.create_backup()
        
        # Encontrar archivos HTML
        html_files = self.find_html_files()
        print(f"📁 Encontrados {len(html_files)} archivos HTML")
        
        # Procesar archivos
        fixed_files = 0
        for file_path in html_files:
            if self.process_file(file_path):
                fixed_files += 1
        
        print("=" * 60)
        print(f"✅ Correcciones completadas!")
        print(f"   - Archivos procesados: {len(html_files)}")
        print(f"   - Archivos corregidos: {fixed_files}")
        print(f"   - Backup guardado en: {self.backup_dir}")
        
        print("\n📋 Siguientes pasos recomendados:")
        print("1. Revisar los cambios en el navegador")
        print("2. Verificar que dropdowns funcionan correctamente")
        print("3. Verificar que accordions funcionan correctamente")
        print("4. Verificar que tooltips funcionan correctamente")
        print("5. Revisar el diseño responsive")
        print("6. Ejecutar pruebas de funcionalidad")
        
        if fixed_files > 0:
            print("\n⚠️  Cambios importantes aplicados:")
            print("   - Clases CSS migradas a Bootstrap 5")
            print("   - Atributos JavaScript actualizados")
            print("   - Atributos duplicados eliminados")
            print("   - Estructuras de accordion corregidas")

def main():
    """Función principal"""
    project_root = Path(__file__).parent
    fixer = BootstrapMigrationFixer(project_root)
    
    print("¿Deseas aplicar las correcciones de migración Bootstrap 5? (y/N): ", end="")
    response = input().strip().lower()
    
    if response == 'y':
        fixer.run_fix()
    else:
        print("Correcciones canceladas.")

if __name__ == "__main__":
    main()
