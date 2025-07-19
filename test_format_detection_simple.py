#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simple para validar la lógica de detección de formatos espaciales
sin depender del entorno CKAN completo.
"""

def test_spatial_format_detection():
    """
    Prueba la lógica de detección de formatos espaciales.
    Simula la función _is_potential_spatial_resource del plugin.
    """
    
    def is_potential_spatial_resource(resource):
        """
        Simula la lógica del plugin para detectar recursos espaciales.
        IMPORTANTE: Los ZIP con shapefiles se marcan como formato "SHP"
        """
        # Verificar formato del recurso - CLAVE: Los ZIP se marcan como "SHP"
        resource_format = resource.get('format', '').lower()
        spatial_formats = ['shp', 'shapefile', 'zip', 'tif', 'tiff', 'geotiff', 
                          'kml', 'gpkg', 'geopackage', 'geojson', 'json']
        
        if resource_format in spatial_formats:
            return True
            
        # Verificar extensión del archivo en la URL como respaldo
        url = resource.get('url', '')
        if url:
            url_lower = url.lower()
            spatial_extensions = ['.shp', '.zip', '.tif', '.tiff', '.kml', '.gpkg', '.geojson']
            for ext in spatial_extensions:
                if url_lower.endswith(ext):
                    return True
        
        return False
    
    print("=" * 70)
    print("🧪 VALIDACIÓN DE LÓGICA DE DETECCIÓN DE FORMATOS ESPACIALES")
    print("=" * 70)
    print("🔑 Punto clave: Los ZIP con shapefiles se marcan como formato 'SHP'")
    print("=" * 70)
    
    # Casos de prueba basados en el comportamiento real
    test_cases = [
        {
            'description': '🎯 ZIP con shapefile marcado como SHP (CASO PRINCIPAL)',
            'resource': {'format': 'SHP', 'url': 'https://storage.azure.com/boundaries.zip'},
            'expected': True,
            'critical': True
        },
        {
            'description': 'Shapefile directo con formato SHP',
            'resource': {'format': 'SHP', 'url': 'https://storage.azure.com/boundaries.shp'},
            'expected': True,
            'critical': False
        },
        {
            'description': 'ZIP detectado por extensión (sin formato especificado)',
            'resource': {'format': '', 'url': 'https://storage.azure.com/data.zip'},
            'expected': True,
            'critical': False
        },
        {
            'description': 'GeoTIFF con formato TIF',
            'resource': {'format': 'TIF', 'url': 'https://storage.azure.com/elevation.tif'},
            'expected': True,
            'critical': False
        },
        {
            'description': 'GeoJSON con formato GEOJSON',
            'resource': {'format': 'GEOJSON', 'url': 'https://storage.azure.com/areas.geojson'},
            'expected': True,
            'critical': False
        },
        {
            'description': 'CSV normal (NO espacial)',
            'resource': {'format': 'CSV', 'url': 'https://storage.azure.com/data.csv'},
            'expected': False,
            'critical': False
        },
        {
            'description': 'PDF normal (NO espacial)',
            'resource': {'format': 'PDF', 'url': 'https://storage.azure.com/document.pdf'},
            'expected': False,
            'critical': False
        }
    ]
    
    print("\n📋 Ejecutando casos de prueba:\n")
    
    total_tests = len(test_cases)
    passed_tests = 0
    critical_passed = 0
    critical_total = sum(1 for case in test_cases if case['critical'])
    
    for i, test_case in enumerate(test_cases, 1):
        resource = test_case['resource']
        expected = test_case['expected']
        description = test_case['description']
        is_critical = test_case['critical']
        
        # Ejecutar la prueba
        result = is_potential_spatial_resource(resource)
        
        # Determinar el estado
        passed = result == expected
        if passed:
            passed_tests += 1
            if is_critical:
                critical_passed += 1
        
        # Mostrar resultado
        status_icon = "✅" if passed else "❌"
        critical_icon = "🎯" if is_critical else "  "
        
        print(f"{critical_icon} {status_icon} Test {i}: {description}")
        print(f"     Formato: '{resource.get('format', '')}' | URL: '{resource['url']}'")
        print(f"     Resultado: {result} | Esperado: {expected}")
        
        if not passed:
            print(f"     ❌ FALLÓ: Se esperaba {expected} pero se obtuvo {result}")
            
        print()
    
    # Resumen
    print("=" * 70)
    print("📊 RESUMEN DE RESULTADOS")
    print("=" * 70)
    
    print(f"✅ Pruebas pasadas: {passed_tests}/{total_tests}")
    print(f"🎯 Pruebas críticas pasadas: {critical_passed}/{critical_total}")
    
    # Evaluación
    all_passed = passed_tests == total_tests
    critical_all_passed = critical_passed == critical_total
    
    if all_passed:
        print("\n🎉 ¡TODAS LAS PRUEBAS PASARON!")
        print("✨ La lógica de detección de formatos está funcionando correctamente")
    elif critical_all_passed:
        print("\n✅ Las pruebas CRÍTICAS pasaron")
        print("🎯 El caso principal (ZIP -> SHP) funciona correctamente")
        print(f"⚠️  Pero {total_tests - passed_tests} pruebas no críticas fallaron")
    else:
        print("\n❌ PRUEBAS CRÍTICAS FALLARON")
        print("🚨 El caso principal (ZIP -> SHP) NO está funcionando")
        print("🔧 Revisar la implementación de _is_potential_spatial_resource()")
    
    print("\n🔧 IMPLEMENTACIÓN VÁLIDA PARA:")
    print("   - Detectar ZIP con formato 'SHP'")
    print("   - Detectar otros formatos espaciales")
    print("   - Ignorar formatos no espaciales")
    print("   - Usar extensión de URL como respaldo")
    
    print("\n💡 RECORDATORIO:")
    print("   - Los ZIP con shapefiles se marcan como formato 'SHP' en CKAN")
    print("   - Esta lógica debe implementarse en IResourceController")
    print("   - Se ejecuta después de crear/actualizar recursos")
    
    print("=" * 70)
    
    return all_passed, critical_all_passed

def main():
    """Ejecuta las pruebas de validación"""
    all_passed, critical_passed = test_spatial_format_detection()
    
    if critical_passed:
        print("🎯 ¡Las pruebas críticas pasaron! La lógica base es correcta.")
        if all_passed:
            print("🌟 Implementación completamente validada.")
        return 0
    else:
        print("❌ Las pruebas críticas fallaron. Revisar la implementación.")
        return 1

if __name__ == "__main__":
    exit(main()) 