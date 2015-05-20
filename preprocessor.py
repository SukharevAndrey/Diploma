from sqlalchemy import and_

from main import file_to_json
from collections import defaultdict
from entities.location import *
from entities.operator import *

class TariffPreprocessor:
    def __init__(self, info, session):
        self.info = info
        self.db_session = session

    def get_country_info(self, name, info):
        country_info = {'name': name}
        if 'cost' in info:
            country_info['cost'] = info['cost']
        if 'operators' in info:
            country_info['operators'] = info['operators']
        return country_info

    def get_operator_info(self, name, info):
        operator_info = {'name': name}

        if 'cost' in info:
            operator_info['cost'] = info['cost']
        elif 'regions' in info:
            operator_info['regions'] = info['regions']

        return operator_info

    def get_region_info(self, name, info):
        region_info = {'name': name,
                       'cost': info['cost']}

        return region_info

    def preprocessed(self):
        home_country_name = 'Russia'
        home_region_name = 'Moskva'
        country_infos = [{'id': 0,
                          'name': 'HOME_COUNTRY',
                          'operators': 0},
                         {'id': 1,
                          'name': 'CIS_COUNTRIES',
                          'cost': 29.0},
                         {'id': 2,
                          'name': 'EUROPE_COUNTRIES',
                          'cost': 49.0},
                         {'id': 3,
                          'name': '|REST_COUNTRIES|',
                          'cost': 70.0}]

        operator_infos = [
            {'id': 0,
             'country': 0,
             'name': 'MTS',
             'regions': 0},
            {'id': 1,
             'country': 0,
             'name': '|REST_OPERATORS|',
             'regions': 1}]

        region_infos = [[{'name': 'HOME_REGION',
                          'operator': 0,
                          'country': 0,
                          'cost': 0.0},
                         {'name': '|REST_REGIONS|',
                          'operator': 0,
                          'country': 0,
                          'cost': 1.5}],
                        [{'name': 'HOME_REGION',
                          'operator': 1,
                          'country': 0,
                          'cost': 1.5},
                         {'name': '|REST_REGIONS|',
                          'operator': 1,
                          'country': 0,
                          'cost': 10.0}]]

        res = {'name': self.info['name'],
               'activation_code': self.info['activation_code'],
               'regional_versions': []}
        reg_version = {'country_name': home_country_name,
                       'region_name': home_region_name,
                       'transition_cost': self.info['transition_cost'],
                       'subscription_cost': self.info['subscription_cost'],
                       }

        country_infos, country_id_match = self._preprocessed_countries(home_country_name, country_infos)
        print(country_infos)
        print(country_id_match)
        operator_infos, operator_id_match = self._preprocessed_operators(operator_infos,
                                                                         country_infos, country_id_match)
        print(operator_infos)
        print(operator_id_match)
        region_infos = self._preprocessed_regions(home_region_name, region_infos)
        print(region_infos)

    def _preprocessed_countries(self, home_country_name, country_infos):
        cis_country_names = set(file_to_json('data/cis_countries.json'))
        europe_country_names = set(file_to_json('data/europe_countries.json'))

        country_id_match = defaultdict(list)
        new_country_infos = {}
        used_countries = []
        next_country_id = 0

        for country in (sorted(country_infos,
                               key=lambda country: country['name'])):
            country_name = country['name']
            country_id = country['id']
            if country_name == 'HOME_COUNTRY':
                used_countries.append(home_country_name)
                country_id_match[country_id].append(next_country_id)

                country_info = self.get_country_info(home_country_name, country)
                new_country_infos[next_country_id] = country_info
                next_country_id += 1
            elif country_name == 'CIS_COUNTRIES':
                for cis_country_name in cis_country_names-{home_country_name}:
                    used_countries.append(cis_country_name)
                    country_id_match[country_id].append(next_country_id)

                    country_info = self.get_country_info(cis_country_name, country)
                    new_country_infos[next_country_id] = country_info
                    next_country_id += 1
            elif country_name == 'EUROPE_COUNTRIES':
                for eu_country_name in europe_country_names-{home_country_name}:
                    used_countries.append(eu_country_name)
                    country_id_match[country_id].append(next_country_id)

                    country_info = self.get_country_info(eu_country_name, country)
                    new_country_infos[next_country_id] = country_info
                    next_country_id += 1
            elif country_name == '|REST_COUNTRIES|':
                rest_countries = self.db_session.query(Country).\
                    filter(~Country.name.in_(used_countries)).all()
                for country_entity in rest_countries:
                    country_id_match[country_id].append(next_country_id)

                    country_info = self.get_country_info(country_entity.name, country)
                    new_country_infos[next_country_id] = country_info
                    next_country_id += 1
            else:
                used_countries.append(country_name)
                country_id_match[country_id].append(next_country_id)

                country_info = self.get_country_info(country_name, country)
                new_country_infos[next_country_id] = country_info
                next_country_id += 1

        return new_country_infos, country_id_match

    def _preprocessed_operators(self, operator_infos, country_infos, country_id_match):
        operator_id_match = defaultdict(list)
        used_operators = []
        new_operator_infos = {}
        next_operator_id = 0

        for operator in sorted(operator_infos, key=lambda operator: operator['name']):
            operator_name = operator['name']
            operator_id = operator['id']
            country_id = operator['country']

            # TODO: Multiple countries match
            country_name = country_infos[country_id_match[country_id][0]]['name']
            country = self.db_session.query(Country).filter_by(name=country_name).one()

            if operator_name == '|REST_OPERATORS|':
                rest_operators = self.db_session.query(MobileOperator).\
                    filter(and_(MobileOperator.country == country,
                                ~MobileOperator.name.in_(used_operators))).all()
                unique_names = set()

                for operator_entity in rest_operators:
                    unique_names.add(operator_entity.name)

                for name in unique_names:
                    operator_id_match[operator_id].append(next_operator_id)

                    operator_info = self.get_operator_info(name, operator)
                    new_operator_infos[next_operator_id] = operator_info
                    next_operator_id += 1
            else:
                used_operators.append(operator_name)
                operator_id_match[operator_id].append(next_operator_id)

                operator_info = self.get_operator_info(operator_name, operator)
                new_operator_infos[next_operator_id] = operator_info
                next_operator_id += 1

        return new_operator_infos, operator_id_match

    def _preprocessed_regions(self, home_region_name, region_infos):
        new_region_infos = {}
        for region_id in range(len(region_infos)):
            used_regions = []
            operator_regions = []

            for region in sorted(region_infos[region_id], key=lambda region: region['name']):
                region_name = region['name']
                region_country_id = region['country']
                region_operator_id = region['operator']

                if region_name == 'HOME_REGION':
                    used_regions.append(home_region_name)

                    region_info = self.get_region_info(home_region_name, region)
                    operator_regions.append(region_info)
                elif region_name == '|REST_REGIONS|':
                    pass
                else:
                    used_regions.append(region_name)

                    region_info = self.get_region_info(region_name, region)
                    operator_regions.append(region_info)

            new_region_infos[region_operator_id] = operator_regions[:]

        return new_region_infos

    def _merged_data(self, country_infos, operator_infos, region_infos):
        return None
