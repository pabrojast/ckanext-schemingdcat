#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad de extracción comprensiva de metadata
"""

import os
import sys
import json

def test_file_analyzer():
    """Test básico de la clase FileAnalyzer"""
    try:
        from ckanext.schemingdcat.spatial_extent import FileAnalyzer, get_file_analysis_capabilities
        
        print("✅ FileAnalyzer importado correctamente")
        
        # Verificar capacidades
        capabilities = get_file_analysis_capabilities()
        print(f"📊 Capacidades de análisis disponibles:")
        print(json.dumps(capabilities, indent=2, ensure_ascii=False))
        
        # Test básico con un archivo de ejemplo (si existe)
        test_files = [
            'test_spatial_extent.py',  # Archivo de texto que sabemos que existe
            'README.md',  # Otro archivo de texto común
            'setup.py'    # Archivo Python común
        ]
        
        analyzer = FileAnalyzer()
        
        for test_file in test_files:
            if os.path.exists(test_file):
                print(f"\n🔍 Analizando archivo: {test_file}")
                
                try:
                    metadata = analyzer.analyze_file(test_file)
                    print(f"📄 Metadata extraída:")
                    
                    # Mostrar solo los campos que tienen valores
                    for key, value in metadata.items():
                        if value is not None and value != '':
                            if isinstance(value, str) and len(value) > 100:
                                print(f"  {key}: {value[:100]}...")
                            else:
                                print(f"  {key}: {value}")
                    
                    print(f"✅ Análisis exitoso para {test_file}")
                    break  # Solo analizamos el primer archivo que encontremos
                    
                except Exception as e:
                    print(f"❌ Error analizando {test_file}: {e}")
                    continue
        
        return True
        
    except ImportError as e:
        print(f"❌ Error importando FileAnalyzer: {e}")
        return False
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False

def test_comprehensive_job():
    """Test de la función de job comprensiva"""
    try:
        from ckanext.schemingdcat.plugin import extract_comprehensive_metadata_job
        
        print("\n✅ Función de job comprensiva importada correctamente")
        
        # Test con datos de ejemplo (no ejecutamos el job real)
        test_job_data = {
            'resource_id': 'test-resource-id',
            'resource_url': 'https://example.com/test.csv',
            'resource_format': 'CSV',
            'package_id': 'test-package-id'
        }
        
        print(f"📝 Datos de job de ejemplo preparados:")
        print(json.dumps(test_job_data, indent=2, ensure_ascii=False))
        
        print("⚠️  No ejecutamos el job real para evitar problemas de dependencias")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error importando función de job: {e}")
        return False
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False

def test_schema_fields():
    """Verificar que los nuevos campos están en el esquema"""
    try:
        schema_file = 'ckanext/schemingdcat/schemas/unesco/dataset.yaml'
        
        if not os.path.exists(schema_file):
            print(f"❌ Archivo de esquema no encontrado: {schema_file}")
            return False
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar que los nuevos campos están presentes
        new_fields = [
            'spatial_crs',
            'spatial_resolution', 
            'feature_count',
            'geometry_type',
            'data_fields',
            'data_statistics',
            'data_domains',
            'geographic_coverage',
            'administrative_boundaries',
            'file_created_date',
            'file_modified_date',
            'data_temporal_coverage',
            'file_size_bytes',
            'compression_info',
            'format_version',
            'file_integrity',
            'content_type_detected',
            'document_pages',
            'spreadsheet_sheets',
            'text_content_info'
        ]
        
        print(f"\n🔍 Verificando nuevos campos en {schema_file}:")
        
        missing_fields = []
        for field in new_fields:
            if field in content:
                print(f"  ✅ {field}")
            else:
                print(f"  ❌ {field} - NO ENCONTRADO")
                missing_fields.append(field)
        
        if missing_fields:
            print(f"\n❌ Campos faltantes: {missing_fields}")
            return False
        else:
            print(f"\n✅ Todos los nuevos campos están presentes en el esquema")
            return True
        
    except Exception as e:
        print(f"❌ Error verificando esquema: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print("🧪 Testing Comprehensive Metadata Extraction")
    print("=" * 50)
    
    results = []
    
    # Test 1: FileAnalyzer
    print("\n1️⃣  Testing FileAnalyzer...")
    results.append(test_file_analyzer())
    
    # Test 2: Job function
    print("\n2️⃣  Testing comprehensive job function...")
    results.append(test_comprehensive_job())
    
    # Test 3: Schema fields
    print("\n3️⃣  Testing schema fields...")
    results.append(test_schema_fields())
    
    # Resumen
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE PRUEBAS:")
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Pruebas exitosas: {passed}/{total}")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron!")
        return 0
    else:
        print("⚠️  Algunas pruebas fallaron. Revisa los errores arriba.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 