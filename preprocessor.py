import json

from sqlalchemy import and_

from tools import file_to_json
from entities.location import *
from entities.operator import *


class TariffPreprocessor:
    def __init__(self, session):
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

    def parse_basic_service(self, home_country_name, home_region_name, country_infos):
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
                local_operator_infos = country['operators']
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

                    if 'regions' in operator:
                        new_region_infos = []
                        used_regions = []
                        local_region_infos = operator['regions']
                        for region in sorted(local_region_infos,
                                             key=lambda region: region['name']):
                            region_name = region['name']
                            if region_name == 'HOME_REGION':
                                # TODO: Don't add if operator has not that region
                                used_regions.append(home_region_name)
                                region_info = self.get_region_info(home_region_name, region)
                                new_region_infos.append(region_info)
                            elif region_name == '|REST_REGIONS|':
                                rest_regions = self.db_session.query(Region).\
                                    join(Region.operators).\
                                    filter(and_(~Region.name.in_(used_regions),
                                                MobileOperator.name == operator_name)).all()
                                for region_entity in rest_regions:
                                    region_info = self.get_region_info(region_entity.name, region)
                                    new_region_infos.append(region_info)
                            else:
                                used_regions.append(region_name)
                                region_info = self.get_region_info(region_name, region)
                                new_region_infos.append(region_info)
                        operator['regions'] = new_region_infos
        return new_country_infos

    def preprocess(self, info, replace=True):
        if replace:
            tariffs_info = info
        else:
            tariffs_info = info.copy()

        for tariff_info in tariffs_info:
            for regional_version in tariff_info['regional_versions']:
                home_country_name = regional_version['country_name']
                home_region_name = regional_version['region_name']
                for service_info in regional_version['basic_services']:
                    if 'countries' in service_info:
                        new_countries_info = self.parse_basic_service(home_country_name,
                                                                home_region_name,
                                                                service_info['countries'])
                        service_info['countries'] = new_countries_info
        if not replace:
            return tariffs_info