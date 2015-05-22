import json


def file_to_json(file_name):
    with open(file_name, encoding='utf-8') as file:
        raw = file.read()
        res = json.loads(raw)
        return res