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

if __name__ == "__main__":
    print("Test file for endpoints - no active tests currently.")
