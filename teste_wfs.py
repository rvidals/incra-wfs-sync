import requests
import json
import xml.etree.ElementTree as ET

url = "http://acervofundiario.incra.gov.br/i3geo/ogc.php?tema=gf_cert_regist_reman"

# Testar com JSON
params_json = {
    'SERVICE': 'WFS',
    'VERSION': '1.1.0',
    'REQUEST': 'GetFeature',
    'TYPENAME': 'ms:gf_cert_regist_reman',
    'OUTPUTFORMAT': 'application/json',
    'MAXFEATURES': 10
}

print("=== TESTE JSON ===")
response = requests.get(url, params=params_json)
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type')}")
print(f"Primeiros 500 caracteres:\n{response.text[:500]}")

# Testar com XML
params_xml = {
    'SERVICE': 'WFS',
    'VERSION': '1.1.0',
    'REQUEST': 'GetFeature',
    'TYPENAME': 'ms:gf_cert_regist_reman',
    'MAXFEATURES': 10
}

print("\n=== TESTE XML ===")
response = requests.get(url, params=params_xml)
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type')}")
print(f"Primeiros 500 caracteres:\n{response.text[:500]}")