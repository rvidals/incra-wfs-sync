import requests
import xml.etree.ElementTree as ET

url = "http://acervofundiario.incra.gov.br/i3geo/ogc.php?tema=gf_cert_regist_reman"

params = {
    'SERVICE': 'WFS',
    'VERSION': '1.1.0',
    'REQUEST': 'GetFeature',
    'TYPENAME': 'ms:gf_cert_regist_reman',
    'MAXFEATURES': 5
}

response = requests.get(url, params=params)
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type')}")

# Parsear XML
root = ET.fromstring(response.text)

# Mostrar estrutura
print("\n=== ESTRUTURA DO XML ===")
for i, elem in enumerate(root.iter()):
    if i < 30:
        print(f"{'  ' * (len(elem.tag.split('}')) - 1)}{elem.tag} - {len(elem)} filhos, text: {elem.text[:50] if elem.text else ''}")

# Buscar features
print("\n=== FEATURES ===")
for member in root.findall('.//featureMember'):
    for feature in member:
        print(f"\nFeature encontrada:")
        for child in feature:
            tag = child.tag.split('}')[-1]
            text = child.text.strip() if child.text else ''
            print(f"  {tag}: {text[:100]}...")