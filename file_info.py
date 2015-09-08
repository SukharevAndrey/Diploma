from tools import file_to_json, file_to_config

USER_GROUPS_FILE = 'data/clusters/customer_clusters.json'
AGREEMENTS_FILE = 'data/clusters/agreement_clusters.json'
ACCOUNTS_FILE = 'data/clusters/account_clusters.json'
DEVICES_FILE = 'data/clusters/device_clusters.json'
DISTRIBUTIONS_FILE = 'data/distributions.json'
OUT_OF_FUNDS_FILE = 'data/out_of_funds.json'

user_groups_info = file_to_json(USER_GROUPS_FILE)
agreements_info = file_to_json(AGREEMENTS_FILE)
accounts_info = file_to_json(ACCOUNTS_FILE)
devices_info = file_to_json(DEVICES_FILE)
distributions_info = file_to_json(DISTRIBUTIONS_FILE)
out_of_funds_info = file_to_json(OUT_OF_FUNDS_FILE)

COUNTRIES_FILE_PATH = 'data/countries.json'
OPERATORS_FILE_PATH = 'data/operators.json'
TARIFFS_FILE_PATH = 'data/mts_tariffs.json'
SERVICES_FILE_PATH = 'data/mts_services.json'
REGIONS_FILE_PATH = 'data/russia_subjects.json'

countries_info = file_to_json(COUNTRIES_FILE_PATH)
regions_info = file_to_json(REGIONS_FILE_PATH)
operators_info = file_to_json(OPERATORS_FILE_PATH)
services_info = file_to_json(SERVICES_FILE_PATH)
tariffs_info = file_to_json(TARIFFS_FILE_PATH)

CONFIG_FILE = 'config.txt'
config_info = file_to_config(CONFIG_FILE)
