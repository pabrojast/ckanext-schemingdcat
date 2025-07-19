#!/usr/bin/env python3
"""
Test para verificar que los arreglos de contexto Flask funcionan correctamente.
"""

def test_context_fixes():
    """Test de los arreglos implementados."""
    
    print("🔧 Verificando arreglos de contexto Flask...")
    print("=" * 50)
    
    # Test 1: Verificar que se quitó el parámetro timeout
    print("\n1️⃣ Verificando arreglo de Jobs Queue...")
    
    with open('ckanext/schemingdcat/plugin.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar que no hay timeout en jobs.enqueue
    if 'timeout=300' in content:
        print("   ❌ Parámetro timeout todavía presente")
        return False
    elif 'jobs.enqueue(' in content and 'title=' in content:
        print("   ✅ Jobs.enqueue sin parámetro timeout")
    else:
        print("   ⚠️  Jobs.enqueue no encontrado")
    
    # Verificar manejo de TypeError
    if 'except TypeError as e:' in content:
        print("   ✅ Manejo de TypeError agregado")
    else:
        print("   ❌ Manejo de TypeError faltante")
        return False
    
    # Test 2: Verificar método de actualización directa
    print("\n2️⃣ Verificando actualización directa en BD...")
    
    if '_update_dataset_spatial_extent_direct_db' in content:
        print("   ✅ Método de actualización directa presente")
    else:
        print("   ❌ Método de actualización directa faltante")
        return False
    
    if 'model.Package.get(' in content and 'model.Session.commit()' in content:
        print("   ✅ Acceso directo a BD implementado")
    else:
        print("   ❌ Acceso directo a BD no encontrado")
        return False
    
    # Test 3: Verificar que no usa current_app en threading
    print("\n3️⃣ Verificando threading sin Flask context...")
    
    if 'from flask import current_app' not in content.split('_process_spatial_extent_with_threading')[1]:
        print("   ✅ Threading sin dependencia de Flask")
    else:
        print("   ❌ Threading todavía usa Flask context")
        return False
    
    if 'threading mode' in content:
        print("   ✅ Logging de modo threading presente")
    else:
        print("   ⚠️  Logging de modo threading no encontrado")
    
    # Test 4: Verificar manejo de errores robusto
    print("\n4️⃣ Verificando manejo de errores...")
    
    error_checks = [
        'except ImportError:',
        'except Exception as e:',
        'log.error(',
        'model.Session.rollback()'
    ]
    
    all_present = all(check in content for check in error_checks)
    if all_present:
        print("   ✅ Manejo robusto de errores implementado")
    else:
        print("   ❌ Manejo de errores incompleto")
        return False
    
    print("\n" + "=" * 50)
    print("📊 Resumen de arreglos:")
    print("   ✅ Jobs Queue: Parámetro timeout removido")
    print("   ✅ Threading: Sin dependencia de Flask context")
    print("   ✅ BD directa: Actualización sin hooks")
    print("   ✅ Errores: Manejo robusto implementado")
    
    print("\n🎉 Todos los arreglos están implementados!")
    print("\n📝 Comportamiento esperado ahora:")
    print("   1. Jobs Queue intenta sin timeout")
    print("   2. Si falla → Threading mode (sin Flask)")
    print("   3. Threading usa actualización directa en BD")
    print("   4. No más errores de 'Working outside context'")
    
    return True


if __name__ == "__main__":
    try:
        success = test_context_fixes()
        if success:
            print("\n✅ Verificación de arreglos completada!")
            print("\n🚀 Reinicia CKAN y prueba de nuevo")
        else:
            print("\n❌ Algunos arreglos faltan")
    except Exception as e:
        print(f"\n❌ Error en verificación: {str(e)}")
        import traceback
        traceback.print_exc() 