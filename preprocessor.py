from sqlalchemy import and_
from sqlalchemy.orm import aliased

from main import file_to_json
from entities.location import *
from entities.operator import *

import json

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
        country_infos = [{'name': 'HOME_COUNTRY',
                          'operators': 0},
                         {'name': 'CIS_COUNTRIES',
                          'cost': 29.0},
                         {'name': 'EUROPE_COUNTRIES',
                          'cost': 49.0},
                         {'name': '|REST_COUNTRIES|',
                          'cost': 70.0}]

        operator_infos = [[{'name': 'MTS',
                            'regions': 0},
                           {'name': '|REST_OPERATORS|',
                            'regions': 1}]]

        region_infos = [[{'name': 'HOME_REGION',
                          'cost': 0.0},
                         {'name': '|REST_REGIONS|',
                          'cost': 1.5}],
                        [{'name': 'HOME_REGION',
                          'cost': 1.5},
                         {'name': '|REST_REGIONS|',
                          'cost': 10.0}]]

        cis_country_names = set(file_to_json('data/cis_countries.json'))
        eu_country_names = set(file_to_json('data/europe_countries.json'))

        new_country_infos = []
        used_countries = []
        for country in sorted(country_infos, key=lambda country: country['name']):
            country_name = country['name']
            if country_name == 'HOME_COUNTRY':
                used_countries.append(home_country_name)
                country_info = self.get_country_info(home_country_name, country)
                new_country_infos.append(country_info)
            elif country_name == 'CIS_COUNTRIES':
                for cis_country_name in cis_country_names-{home_country_name}:
                    used_countries.append(cis_country_name)
                    country_info = self.get_country_info(cis_country_name, country)
                    new_country_infos.append(country_info)
            elif country_name == 'EUROPE_COUNTRIES':
                for eu_country_name in eu_country_names-{home_country_name}:
                    used_countries.append(eu_country_name)
                    country_info = self.get_country_info(eu_country_name, country)
                    new_country_infos.append(country_info)
            elif country_name == '|REST_COUNTRIES|':
                rest_countries = self.db_session.query(Country).\
                    filter(~Country.name.in_(used_countries)).all()
                for country_entity in rest_countries:
                    country_info = self.get_country_info(country_entity.name, country)
                    new_country_infos.append(country_info)
            else:
                used_countries.append(home_country_name)
                country_info = self.get_country_info(country_name, country)
                new_country_infos.append(country_info)

        for country in new_country_infos:
            country_name = country['name']
            country_entity = self.db_session.query(Country).filter_by(name=country_name).one()
            if 'operators' in country:
                new_operator_infos = []
                used_operators = []
                local_operator_infos = operator_infos[country['operators']]
                for operator in sorted(local_operator_infos,
                                       key=lambda operator: operator['name']):
                    operator_name = operator['name']
                    if operator_name == '|REST_OPERATORS|':
                        rest_operators = self.db_session.query(MobileOperator).\
                            filter(and_(MobileOperator.country == country_entity,
                                        ~MobileOperator.name.in_(used_operators))).all()

                        unique_names = set()
                        for operator_entity in rest_operators:
                            unique_names.add(operator_entity.name)

                        for name in unique_names:
                            operator_info = self.get_operator_info(name, operator)
                            new_operator_infos.append(operator_info)
                    else:
                        used_operators.append(operator_name)
                        operator_info = self.get_operator_info(operator_name, operator)
                        new_operator_infos.append(operator_info)
                country['operators'] = new_operator_infos

                for operator in new_operator_infos:
                    operator_name = operator['name']
                    stmt = self.db_session.query(MobileOperator).\
                        filter_by(name=operator_name, country=country_entity).subquery()
                    local_operators = aliased(MobileOperator, stmt)

                    if 'regions' in operator:
                        new_region_infos = []
                        used_regions = []
                        local_region_infos = region_infos[operator['regions']]
                        for region in sorted(local_region_infos,
                                             key=lambda region: region['name']):
                            region_name = region['name']
                            if region_name == 'HOME_REGION':
                                # TODO: Don't add if operator has not that region
                                region_entity = self.db_session.query(Region).filter_by(country=country_entity,
                                                                                        name=home_region_name).one()
                                try:
                                    region_operator = self.db_session.query(local_operators).\
                                        filter_by(region=region_entity).one()
                                except:
                                    pass
                                used_regions.append(home_region_name)
                                region_info = self.get_region_info(home_region_name, region)
                                new_region_infos.append(region_info)
                            elif region_name == '|REST_REGIONS|':
                                pass
                            else:
                                used_regions.append(region_name)
                                region_info = self.get_region_info(region_name, region)
                                new_region_infos.append(region_info)
                        operator['regions'] = new_region_infos

        with open('data/preprocessed_tariffs.json', 'w', encoding='utf-8') as file:
            file.write(json.dumps(new_country_infos, indent=2))

