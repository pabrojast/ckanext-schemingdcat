#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para validar la extracción de extensión espacial post-creación de RECURSOS.

Este script prueba que la nueva funcionalidad de extracción de extensión espacial
funciona correctamente después de crear o actualizar un RECURSO (usando IResourceController),
especialmente para archivos ZIP que se marcan con formato "SHP".
"""

import sys
import os
import tempfile
import json

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

def test_is_potential_spatial_resource():
    """Prueba la función _is_potential_spatial_resource del SchemingDCATDatasetsPlugin"""
    print("🧪 Probando _is_potential_spatial_resource...")
    
    # Import the plugin
    from ckanext.schemingdcat.plugin import SchemingDCATDatasetsPlugin
    
    plugin = SchemingDCATDatasetsPlugin()
    
    # Test cases - IMPORTANTE: Los ZIP se marcan como formato "SHP"
    test_resources = [
        {'format': 'SHP', 'url': 'http://example.com/shapefile.zip', 'expected': True, 'description': 'ZIP con formato SHP'},
        {'format': 'SHP', 'url': 'http://example.com/boundaries.shp', 'expected': True, 'description': 'Shapefile directo'},
        {'format': 'CSV', 'url': 'http://example.com/data.csv', 'expected': False, 'description': 'CSV normal'},
        {'format': 'PDF', 'url': 'http://example.com/doc.pdf', 'expected': False, 'description': 'PDF normal'},
        {'format': '', 'url': 'http://example.com/data.zip', 'expected': True, 'description': 'ZIP detectado por extensión'},
        {'format': '', 'url': 'http://example.com/data.geojson', 'expected': True, 'description': 'GeoJSON por extensión'},
        {'format': 'TIF', 'url': 'http://example.com/raster.tif', 'expected': True, 'description': 'GeoTIFF'},
        {'format': 'GEOJSON', 'url': 'http://example.com/boundaries.geojson', 'expected': True, 'description': 'GeoJSON'},
    ]
    
    all_passed = True
    for i, test_case in enumerate(test_resources):
        expected = test_case.pop('expected')
        description = test_case.pop('description')
        result = plugin._is_potential_spatial_resource(test_case)
        status = "✅" if result == expected else "❌"
        print(f"  {status} Test {i+1}: {description}")
        print(f"       format='{test_case.get('format', '')}', url='{test_case['url']}' -> {result} (expected: {expected})")
        if result != expected:
            all_passed = False
    
    print(f"🎯 Resultado: {'Todas las pruebas pasaron' if all_passed else 'Algunas pruebas fallaron'}")
    return all_passed

def test_spatial_extent_module_availability():
    """Prueba que el módulo de extensión espacial esté disponible"""
    print("\n🧪 Probando disponibilidad del módulo de extensión espacial...")
    
    try:
        from ckanext.schemingdcat.spatial_extent import extent_extractor
        print("  ✅ Módulo de extensión espacial disponible")
        
        # Test basic functionality
        spatial_extensions = extent_extractor.SUPPORTED_EXTENSIONS
        print(f"  📋 Extensiones soportadas: {list(spatial_extensions.keys())}")
        
        # Test ZIP shapefile support
        zip_supported = 'zip' in spatial_extensions
        print(f"  📦 Soporte para ZIP: {'✅' if zip_supported else '❌'}")
        
        return True
    except ImportError as e:
        print(f"  ❌ Módulo no disponible: {e}")
        return False

def test_resource_controller_integration():
    """Prueba la integración con SchemingDCATDatasetsPlugin (IResourceController)"""
    print("\n🧪 Probando integración con IResourceController...")
    
    try:
        from ckanext.schemingdcat.plugin import SchemingDCATDatasetsPlugin
        
        plugin = SchemingDCATDatasetsPlugin()
        
        # Test that the new methods exist
        methods_to_check = [
            '_process_spatial_extent_extraction_for_resource',
            '_is_potential_spatial_resource', 
            '_extract_spatial_extent_from_resource',
            '_update_dataset_spatial_extent',
            'after_create',  # IResourceController hook
            'after_update'   # IResourceController hook
        ]
        
        all_methods_exist = True
        for method_name in methods_to_check:
            if hasattr(plugin, method_name):
                print(f"  ✅ Método {method_name} existe")
            else:
                print(f"  ❌ Método {method_name} no existe")
                all_methods_exist = False
        
        return all_methods_exist
        
    except ImportError as e:
        print(f"  ❌ Error importando SchemingDCATDatasetsPlugin: {e}")
        return False

def test_mock_resource_processing():
    """Simula el procesamiento de recursos espaciales individuales"""
    print("\n🧪 Simulando procesamiento de recursos espaciales individuales...")
    
    try:
        from ckanext.schemingdcat.plugin import SchemingDCATDatasetsPlugin
        
        plugin = SchemingDCATDatasetsPlugin()
        
        # Mock resources - casos típicos
        mock_resources = [
            {
                'id': 'resource-zip-shp',
                'format': 'SHP',  # CLAVE: ZIP se marca como SHP
                'url': 'https://example.com/boundaries.zip',
                'package_id': 'dataset-123'
            },
            {
                'id': 'resource-geotiff',
                'format': 'TIF',
                'url': 'https://example.com/elevation.tif',
                'package_id': 'dataset-456'
            },
            {
                'id': 'resource-csv',
                'format': 'CSV',
                'url': 'https://example.com/data.csv',
                'package_id': 'dataset-789'
            },
            {
                'id': 'resource-geojson',
                'format': 'GEOJSON',
                'url': 'https://example.com/areas.geojson',
                'package_id': 'dataset-abc'
            }
        ]
        
        # Test resource filtering
        spatial_resources = []
        for resource in mock_resources:
            if plugin._is_potential_spatial_resource(resource):
                spatial_resources.append(resource)
        
        print(f"  📊 Recursos totales: {len(mock_resources)}")
        print(f"  🗺️  Recursos espaciales detectados: {len(spatial_resources)}")
        
        for resource in spatial_resources:
            print(f"    - {resource['format']}: {resource['url']} (ID: {resource['id']})")
        
        # Should find 3 spatial resources (SHP/ZIP, TIF, GEOJSON)
        expected_spatial_count = 3
        success = len(spatial_resources) == expected_spatial_count
        
        print(f"  🎯 Resultado: {'✅ Correcto' if success else '❌ Incorrecto'} (esperado: {expected_spatial_count}, obtenido: {len(spatial_resources)})")
        
        # Test specific case: ZIP marked as SHP
        zip_shp_resource = mock_resources[0]  # First resource (ZIP marked as SHP)
        is_spatial = plugin._is_potential_spatial_resource(zip_shp_resource)
        print(f"  🔍 Caso especial ZIP->SHP: {'✅ Detectado correctamente' if is_spatial else '❌ No detectado'}")
        
        return success and is_spatial
        
    except Exception as e:
        print(f"  ❌ Error en simulación: {e}")
        return False

def test_format_detection_logic():
    """Prueba específicamente la lógica de detección de formatos para ZIP/SHP"""
    print("\n🧪 Probando lógica específica de detección ZIP/SHP...")
    
    try:
        from ckanext.schemingdcat.plugin import SchemingDCATDatasetsPlugin
        
        plugin = SchemingDCATDatasetsPlugin()
        
        test_cases = [
            {
                'description': 'ZIP con shapefile marcado como SHP',
                'resource': {'format': 'SHP', 'url': 'https://storage.azure.com/boundaries.zip'},
                'expected': True
            },
            {
                'description': 'Shapefile directo',
                'resource': {'format': 'SHP', 'url': 'https://storage.azure.com/boundaries.shp'},
                'expected': True
            },
            {
                'description': 'ZIP detectado por extensión (sin formato)',
                'resource': {'format': '', 'url': 'https://storage.azure.com/data.zip'},
                'expected': True
            },
            {
                'description': 'Archivo normal CSV',
                'resource': {'format': 'CSV', 'url': 'https://storage.azure.com/data.csv'},
                'expected': False
            }
        ]
        
        all_passed = True
        for i, test_case in enumerate(test_cases):
            result = plugin._is_potential_spatial_resource(test_case['resource'])
            expected = test_case['expected']
            status = "✅" if result == expected else "❌"
            
            print(f"  {status} {test_case['description']}")
            print(f"       {result} (esperado: {expected})")
            
            if result != expected:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"  ❌ Error en prueba de detección: {e}")
        return False

def main():
    """Ejecuta todas las pruebas"""
    print("=" * 80)
    print("🧪 PRUEBAS DE EXTRACCIÓN ESPACIAL POST-CREACIÓN DE RECURSOS")
    print("=" * 80)
    print("✨ Usando IResourceController para manejar recursos individuales")
    print("🔑 Clave: Los ZIP con shapefiles se marcan con formato 'SHP'")
    print("=" * 80)
    
    results = []
    
    # Run tests
    results.append(test_spatial_extent_module_availability())
    results.append(test_resource_controller_integration())
    results.append(test_format_detection_logic())
    results.append(test_is_potential_spatial_resource())
    results.append(test_mock_resource_processing())
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 80)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Pruebas pasadas: {passed}/{total}")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! La implementación está lista.")
        print("\n📋 PRÓXIMOS PASOS:")
        print("1. Reiniciar el servidor CKAN para aplicar los cambios")
        print("2. Crear un dataset y agregar un recurso con archivo ZIP")
        print("3. Marcar el formato del recurso como 'SHP' (no 'ZIP')")
        print("4. Guardar el recurso")
        print("5. Verificar que el campo spatial_extent del dataset se llene automáticamente")
        print("6. Revisar los logs para confirmar que la extracción se ejecuta después de crear el recurso")
        print("\n🔧 FLUJO CORRECTO:")
        print("   Crear recurso → Hook after_create de IResourceController → Extracción espacial → Actualizar dataset")
    else:
        print("⚠️  Algunas pruebas fallaron. Revisar la implementación.")
    
    print("=" * 80)

if __name__ == "__main__":
    main() 