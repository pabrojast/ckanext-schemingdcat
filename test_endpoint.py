#!/usr/bin/env python3
"""
Script para probar directamente el endpoint de extracción de extensión espacial.
"""

import requests
import json
import tempfile
import zipfile
import os

def create_test_shapefile_zip():
    """Crear un ZIP de prueba con archivos de shapefile simulados."""
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
        with zipfile.ZipFile(tmp_zip.name, 'w') as zip_ref:
            # Agregar archivos simulados de shapefile
            zip_ref.writestr('test.shp', b'dummy shapefile content')
            zip_ref.writestr('test.shx', b'dummy index content')
            zip_ref.writestr('test.dbf', b'dummy database content')
            zip_ref.writestr('test.prj', b'dummy projection content')
        return tmp_zip.name

def test_spatial_extent_endpoint(base_url='http://localhost:5000'):
    """Probar el endpoint de extracción de extensión espacial."""
    
    print("=== Prueba del Endpoint de Extracción Espacial ===")
    
    # Crear archivo ZIP de prueba
    zip_file_path = create_test_shapefile_zip()
    print(f"Archivo ZIP de prueba creado: {zip_file_path}")
    
    try:
        # Enviar archivo al endpoint
        url = f"{base_url}/api/extract-spatial-extent"
        print(f"Enviando solicitud a: {url}")
        
        with open(zip_file_path, 'rb') as f:
            files = {'file': ('test_shapefile.zip', f, 'application/zip')}
            response = requests.post(url, files=files, timeout=30)
        
        print(f"Código de respuesta: {response.status_code}")
        print(f"Contenido de respuesta: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print("Respuesta JSON:")
                print(json.dumps(result, indent=2))
                
                if result.get('success'):
                    print("✓ Extracción exitosa!")
                    if 'extent' in result:
                        print("✓ Extensión espacial encontrada!")
                else:
                    print("✗ Extracción fallida:", result.get('error', 'Error desconocido'))
            except json.JSONDecodeError as e:
                print(f"✗ Error decodificando JSON: {e}")
        else:
            print(f"✗ Error HTTP: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Error de conexión: {e}")
        print("Asegúrate de que CKAN esté ejecutándose en", base_url)
        
    finally:
        # Limpiar archivo temporal
        try:
            os.unlink(zip_file_path)
            print(f"Archivo temporal eliminado: {zip_file_path}")
        except OSError:
            pass

if __name__ == "__main__":
    # Puedes cambiar la URL base si CKAN está en otra dirección
    test_spatial_extent_endpoint()
