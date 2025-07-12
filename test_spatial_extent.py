#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad de extracción de extensión espacial.
"""

import os
import sys
import tempfile
import zipfile

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ckanext'))

from schemingdcat.spatial_extent import SpatialExtentExtractor

def test_zip_detection():
    """Prueba la detección de archivos ZIP que contienen shapefiles."""
    
    extractor = SpatialExtentExtractor()
    
    # Crear un ZIP de prueba con archivos de shapefile simulados
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
        try:
            with zipfile.ZipFile(tmp_zip.name, 'w') as zip_ref:
                # Agregar archivos simulados de shapefile
                zip_ref.writestr('test.shp', b'dummy shapefile content')
                zip_ref.writestr('test.shx', b'dummy index content')
                zip_ref.writestr('test.dbf', b'dummy database content')
                zip_ref.writestr('test.prj', b'dummy projection content')
            
            # Probar detección
            print(f"Archivo ZIP de prueba: {tmp_zip.name}")
            print(f"¿Es un ZIP de shapefile?: {extractor._is_shapefile_zip(tmp_zip.name)}")
            print(f"¿Se puede extraer extensión?: {extractor.can_extract_extent(tmp_zip.name)}")
            
        finally:
            # Limpiar archivo temporal (Windows puede tener problemas con archivos abiertos)
            try:
                os.unlink(tmp_zip.name)
            except PermissionError:
                # En Windows, a veces el archivo está bloqueado temporalmente
                pass

def test_available_handlers():
    """Prueba qué manejadores están disponibles."""
    
    extractor = SpatialExtentExtractor()
    
    print("Manejadores disponibles:")
    for format_type, available in extractor.available_handlers.items():
        status = "✓" if available else "✗"
        print(f"  {status} {format_type}")

def main():
    print("=== Prueba de Extracción de Extensión Espacial ===\n")
    
    print("1. Verificando manejadores disponibles:")
    test_available_handlers()
    
    print("\n2. Probando detección de ZIP de shapefile:")
    test_zip_detection()
    
    print("\n=== Prueba completada ===")

if __name__ == "__main__":
    main()
