import yaml
from urllib.parse import urlparse
import os
import shutil

def append_to_file(file_path, data, lang=None):
    field_name = data["field_name"]
    with open(f'./output/{field_name}/{file_path}', 'a') as file:
        # Check if "label" and "en" keys exist in data
        if "label" in data and "en" in data["label"]:
            file.write(f'\n\n# {data["label"]["en"]} - Schema field_name: {data["field_name"]}\n')
        else:
            file.write(f'\n\n# Schema field_name: {data["field_name"]}\n')
        for choice in data['choices']:
            value = extract_value(choice['value'])
            file.write(f'nmsgid "{value}"\n')  # Add a newline at the beginning
            if lang:
                label = choice['label'].get(lang, '')
                file.write(f'msgstr "{label}"\n\n')
            else:
                file.write('msgstr ""\n\n')

def read_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def extract_value(value):
    if value.startswith('http'):
        return urlparse(value).path.split('/')[-1]
    return value

def write_to_file(file_path, data, lang=None):
    field_name = data["field_name"]
    os.makedirs(f'output/{field_name}', exist_ok=True)
    with open(f'output/{field_name}/{file_path}', 'w') as file:
        # Check if "label" and "en" keys exist in data
        if "label" in data and "en" in data["label"]:
            file.write(f'# {data["label"]["en"]} - Schema field_name: {data["field_name"]}\n')
        else:
            file.write(f'# Schema field_name: {data["field_name"]}\n')
        for choice in data['choices']:
            value = extract_value(choice['value'])
            file.write(f'msgid "{value}"\n')
            if lang:
                label = choice['label'].get(lang, '')
                file.write(f'msgstr "{label}"\n\n')
            else:
                file.write('msgstr ""\n\n')

def create_directories(langs, field_name):
    for lang in langs:
        os.makedirs(f'output/{field_name}/{lang}/LC_MESSAGES', exist_ok=True)

def get_languages(data):
    return set(lang for choice in data['choices'] for lang in choice['label'])

def main():
    # Change working directory to the location of this script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    data = read_yaml('input/input.yaml')
    field_name = data["field_name"]
    langs = get_languages(data)
    create_directories(langs, field_name)
    for lang in langs:
        # Copy existing file to output directory
        shutil.copy(f'../{lang}/LC_MESSAGES/ckanext-schemingdcat.po', f'./output/{field_name}/{lang}/LC_MESSAGES/ckanext-schemingdcat.po')
        append_to_file(f'{lang}/LC_MESSAGES/ckanext-schemingdcat.po', data, lang)
    # Copy existing .pot file to output directory
    shutil.copy('../ckanext-schemingdcat.pot', f'./output/{field_name}/ckanext-schemingdcat.pot')
    append_to_file('ckanext-schemingdcat.pot', data)

if __name__ == "__main__":
    main()