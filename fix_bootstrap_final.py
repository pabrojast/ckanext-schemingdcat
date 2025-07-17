#!/usr/bin/env python3
"""
Script adicional para corregir problemas específicos restantes
en la migración de Bootstrap 3 a Bootstrap 5
"""

import os
import re
import shutil
from pathlib import Path

class BootstrapFinalFixes:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.templates_dir = self.project_root / "ckanext" / "schemingdcat" / "templates"
        
    def fix_api_examples_accordion(self):
        """Corregir los accordions en los ejemplos de API"""
        api_examples_dir = self.templates_dir / "api_examples"
        
        for file_path in api_examples_dir.glob("*.html"):
            print(f"🔧 Corrigiendo accordion en: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Corregir la estructura de accordion completa
            # Cambiar panel card-default por card
            content = re.sub(r'<div class="panel card-default">', '<div class="card">', content)
            
            # Cambiar card-heading por card-header
            content = re.sub(r'<div class="card-heading">', '<div class="card-header">', content)
            
            # Cambiar card-collapse por collapse
            content = re.sub(r'class="card-collapse collapse"', 'class="collapse"', content)
            
            # Cambiar card-body por card-body (ya está bien)
            # content = re.sub(r'<div class="card-body">', '<div class="card-body">', content)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"  ✅ Corregido: {file_path}")
    
    def fix_ajax_snippet_accordion(self):
        """Corregir el accordion en el snippet de AJAX"""
        ajax_snippet_path = self.templates_dir / "ajax_snippets" / "scd_api_info.html"
        
        if ajax_snippet_path.exists():
            print(f"🔧 Corrigiendo accordion en: {ajax_snippet_path}")
            
            with open(ajax_snippet_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Similar a los ejemplos de API
            content = re.sub(r'<div class="panel card-default">', '<div class="card">', content)
            content = re.sub(r'<div class="card-heading">', '<div class="card-header">', content)
            content = re.sub(r'class="card-collapse collapse"', 'class="collapse"', content)
            
            with open(ajax_snippet_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"  ✅ Corregido: {ajax_snippet_path}")
    
    def fix_remaining_btn_default(self):
        """Buscar y corregir cualquier btn-default que quede"""
        print("🔍 Buscando btn-default restantes...")
        
        # Archivos específicos que revisamos antes
        files_to_check = [
            "schemingdcat/package/resource_read.html",
            "schemingdcat/snippets/captcha_form.html",
        ]
        
        for file_rel_path in files_to_check:
            file_path = self.templates_dir / file_rel_path
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'btn-default' in content:
                    print(f"🔧 Corrigiendo btn-default en: {file_path}")
                    content = re.sub(r'\bbtn-default\b', 'btn-secondary', content)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"  ✅ Corregido: {file_path}")
    
    def fix_dropdown_caret(self):
        """Corregir el caret de dropdown que puede no estar funcionando"""
        print("🔧 Revisando elementos caret en dropdowns...")
        
        # Buscar archivos que contengan caret
        for file_path in self.templates_dir.rglob("*.html"):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if '<span class="caret">' in content:
                print(f"🔧 Actualizando caret en: {file_path}")
                
                # En Bootstrap 5, el caret se maneja automáticamente
                # Pero podemos mantenerlo o cambiarlo por una clase más específica
                content = re.sub(
                    r'<span class="caret"></span>',
                    '<i class="fas fa-caret-down"></i>',
                    content
                )
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"  ✅ Caret actualizado: {file_path}")
    
    def add_bootstrap_5_compatibility_css(self):
        """Crear un archivo CSS con clases de compatibilidad para Bootstrap 5"""
        css_path = self.project_root / "ckanext" / "schemingdcat" / "assets" / "css" / "bootstrap5-compatibility.css"
        
        css_content = """
/* Bootstrap 5 Compatibility CSS for SchemingDCAT */
/* Este archivo proporciona clases de compatibilidad adicionales */

/* Compatibilidad para badges que pueden necesitar ajustes */
.badge {
    display: inline-block;
    padding: 0.25em 0.5em;
    font-size: 0.875em;
    font-weight: 500;
    line-height: 1;
    text-align: center;
    white-space: nowrap;
    vertical-align: baseline;
    border-radius: 0.25rem;
}

/* Asegurar que los dropdowns funcionen correctamente */
.dropdown-toggle::after {
    display: inline-block;
    margin-left: 0.255em;
    vertical-align: 0.255em;
    content: "";
    border-top: 0.3em solid;
    border-right: 0.3em solid transparent;
    border-bottom: 0;
    border-left: 0.3em solid transparent;
}

/* Mejorar el espaciado de los elementos flotantes */
.float-start {
    float: left !important;
}

.float-end {
    float: right !important;
}

/* Asegurar que los accordions funcionen correctamente */
.accordion-button {
    background-color: transparent;
    border: 0;
    padding: 0.5rem 1rem;
    text-align: left;
    width: 100%;
    cursor: pointer;
}

.accordion-button:not(.collapsed) {
    color: #0c63e4;
    background-color: #e7f1ff;
}

/* Ajustes para cards */
.card {
    position: relative;
    display: flex;
    flex-direction: column;
    min-width: 0;
    word-wrap: break-word;
    background-color: #fff;
    background-clip: border-box;
    border: 1px solid rgba(0, 0, 0, 0.125);
    border-radius: 0.25rem;
}

.card-header {
    padding: 0.5rem 1rem;
    margin-bottom: 0;
    background-color: rgba(0, 0, 0, 0.03);
    border-bottom: 1px solid rgba(0, 0, 0, 0.125);
}

.card-body {
    flex: 1 1 auto;
    padding: 1rem;
}

/* Ajustes para formularios */
.form-label {
    margin-bottom: 0.5rem;
    font-weight: 500;
}

.form-text {
    margin-top: 0.25rem;
    font-size: 0.875em;
    color: #6c757d;
}

.mb-3 {
    margin-bottom: 1rem !important;
}

/* Ajustes para botones secundarios */
.btn-secondary {
    color: #fff;
    background-color: #6c757d;
    border-color: #6c757d;
}

.btn-secondary:hover {
    color: #fff;
    background-color: #5c636a;
    border-color: #565e64;
}

/* Asegurar que los tooltips funcionen */
.tooltip {
    position: absolute;
    z-index: 1070;
    display: block;
    margin: 0;
    font-style: normal;
    font-weight: 400;
    line-height: 1.5;
    text-align: left;
    text-decoration: none;
    text-shadow: none;
    text-transform: none;
    letter-spacing: normal;
    word-break: normal;
    word-spacing: normal;
    white-space: normal;
    line-break: auto;
    font-size: 0.875rem;
    word-wrap: break-word;
    opacity: 0;
}

/* Ajustes específicos para el tema schemingdcat */
.dataset-badges .badge {
    margin-right: 0.5rem;
    margin-bottom: 0.5rem;
}

.download-links .dropdown-menu {
    min-width: 10rem;
}

.format_icon {
    width: 16px;
    height: 16px;
    margin-right: 0.5rem;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .float-end {
        float: none !important;
        display: block;
        margin-top: 0.5rem;
    }
    
    .float-start {
        float: none !important;
        display: block;
        margin-bottom: 0.5rem;
    }
}
"""
        
        # Crear el directorio si no existe
        css_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css_content)
        
        print(f"✅ Archivo CSS de compatibilidad creado: {css_path}")
    
    def update_webassets_config(self):
        """Actualizar configuración de webassets para incluir el CSS de compatibilidad"""
        webassets_path = self.project_root / "ckanext" / "schemingdcat" / "assets" / "webassets.yml"
        
        if webassets_path.exists():
            print(f"🔧 Actualizando webassets.yml: {webassets_path}")
            
            with open(webassets_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Agregar el CSS de compatibilidad si no está presente
            if 'bootstrap5-compatibility.css' not in content:
                # Buscar la sección de CSS y agregar el archivo
                css_section = re.search(r'(schemingdcat-css:.*?depends:\s*)(.*?)(filters:)', content, re.DOTALL)
                if css_section:
                    depends_section = css_section.group(2)
                    if 'css/bootstrap5-compatibility.css' not in depends_section:
                        new_depends = depends_section.rstrip() + '\n    - css/bootstrap5-compatibility.css'
                        content = content.replace(css_section.group(2), new_depends)
                
                with open(webassets_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"  ✅ webassets.yml actualizado")
            else:
                print(f"  ⚪ webassets.yml ya contiene el CSS de compatibilidad")
    
    def run_final_fixes(self):
        """Ejecutar todas las correcciones finales"""
        print("🔧 Ejecutando correcciones finales de Bootstrap 5")
        print("=" * 60)
        
        # Ejecutar todas las correcciones
        self.fix_api_examples_accordion()
        self.fix_ajax_snippet_accordion()
        self.fix_remaining_btn_default()
        self.fix_dropdown_caret()
        self.add_bootstrap_5_compatibility_css()
        self.update_webassets_config()
        
        print("=" * 60)
        print("✅ Correcciones finales completadas!")
        print("\n📋 Resumen de cambios:")
        print("   - Accordions en ejemplos de API corregidos")
        print("   - Accordions en AJAX snippets corregidos")
        print("   - Elementos btn-default restantes corregidos")
        print("   - Carets de dropdown actualizados")
        print("   - CSS de compatibilidad Bootstrap 5 creado")
        print("   - webassets.yml actualizado")
        
        print("\n🎯 Próximos pasos:")
        print("1. Reiniciar el servidor CKAN")
        print("2. Verificar que los dropdowns funcionan")
        print("3. Verificar que los accordions se expanden/contraen")
        print("4. Verificar que los tooltips aparecen")
        print("5. Probar en diferentes dispositivos (responsive)")
        print("6. Verificar que los badges se muestran correctamente")

def main():
    """Función principal"""
    project_root = Path(__file__).parent
    fixer = BootstrapFinalFixes(project_root)
    
    print("¿Deseas aplicar las correcciones finales de Bootstrap 5? (y/N): ", end="")
    response = input().strip().lower()
    
    if response == 'y':
        fixer.run_final_fixes()
    else:
        print("Correcciones finales canceladas.")

if __name__ == "__main__":
    main()
