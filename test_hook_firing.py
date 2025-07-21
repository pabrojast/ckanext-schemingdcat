#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar que los hooks IResourceController se ejecutan correctamente.
"""

import os
import sys

def test_hook_system():
    """Prueba básica del sistema de hooks"""
    print("🧪 VERIFICANDO SISTEMA DE HOOKS IResourceController")
    print("=" * 60)
    
    try:
        # Simular configuración CKAN
        sys.path.insert(0, os.path.dirname(__file__))
        
        # Importar el plugin
        from ckanext.schemingdcat.plugin import SchemingDCATDatasetsPlugin
        
        # Crear instancia del plugin
        plugin = SchemingDCATDatasetsPlugin()
        
        print("✅ Plugin importado correctamente")
        print(f"✅ Plugin class: {plugin.__class__.__name__}")
        
        # Verificar que tiene los métodos necesarios
        required_methods = ['after_create', 'after_update', '_process_spatial_extent_extraction_for_resource', '_is_potential_spatial_resource']
        
        for method in required_methods:
            if hasattr(plugin, method):
                print(f"✅ Método {method} disponible")
            else:
                print(f"❌ Método {method} NO disponible")
                return False
        
        # Test del método _is_potential_spatial_resource
        print("\n🔍 PROBANDO DETECCIÓN DE ARCHIVOS ESPACIALES:")
        
        test_resources = [
            {'id': 'test1', 'format': 'SHP', 'url': 'test.zip'},
            {'id': 'test2', 'format': 'ZIP', 'url': 'test.zip'},
            {'id': 'test3', 'format': 'TIF', 'url': 'test.tif'},
            {'id': 'test4', 'format': 'PDF', 'url': 'test.pdf'},
            {'id': 'test5', 'format': '', 'url': 'shapefile.zip'},
        ]
        
        for resource in test_resources:
            is_spatial = plugin._is_potential_spatial_resource(resource)
            status = "✅ ESPACIAL" if is_spatial else "❌ NO ESPACIAL"
            print(f"  {status}: {resource['format']} - {resource['url']}")
        
        print("\n🎯 RECOMENDACIONES:")
        print("1. Verificar que 'schemingdcat_datasets' esté en production.ini")
        print("2. Subir un archivo ZIP con shapefile")
        print("3. Asegurarse de que el formato se marque como 'SHP' (no 'ZIP')")
        print("4. Revisar los logs para ver los emojis de debugging")
        print("5. Worker debe estar corriendo: `ckan -c production.ini jobs worker`")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error importando: {e}")
        return False
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False

if __name__ == "__main__":
    success = test_hook_system()
    if success:
        print("\n🎉 Sistema básico parece estar funcionando!")
        print("📋 Ahora sube un archivo ZIP con shapefile para probar")
    else:
        print("\n⚠️ Hay problemas en el sistema")
    
    sys.exit(0 if success else 1) 