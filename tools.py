import json
from distribution import Distribution


def file_to_json(file_name):
    with open(file_name, encoding='utf-8') as file:
        raw = file.read()
        res = json.loads(raw)
        return res


def distribution_from_list(records_info):
    record_names = []
    record_percentages = []
    for record_info in records_info:
        record_name = record_info['name']
        record_names.append(record_name)

        record_percentage = record_info['percentage']
        record_percentages.append(record_percentage)

    dist_info = {
        'max_values': len(record_names),
        'values': record_names,
        'probabilities': record_percentages
    }

    return Distribution(info=dist_info)
