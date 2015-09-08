import json

from distribution import Distribution


def file_to_json(file_name):
    with open(file_name, encoding='utf-8') as file:
        raw = file.read()
        res = json.loads(raw)
        return res


def file_to_config(file_name):
    with open(file_name, encoding='utf-8') as file:
        raw_main = file.readline()
        _, main_base_conf = list(map(str.strip, raw_main.split('=')))
        raw_test = file.readline()
        _, test_base_conf = list(map(str.strip, raw_test.split('=')))
        return {'main': main_base_conf, 'test': test_base_conf}


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
