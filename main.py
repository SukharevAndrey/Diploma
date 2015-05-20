from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import scoped_session, sessionmaker

from entities.customer import *
from entities.location import *
from entities.payment import *
from entities.service import *
from entities.operator import *

from base import Base
from random_data import *
from transliterate import translit
import json
from collections import defaultdict

POOL_SIZE = 20

COUNTRIES_FILE_PATH = 'data/countries.json'
OPERATORS_FILE_PATH = 'data/operators.json'
TARIFFS_FILE_PATH = 'data/mts_tariffs.json'
SERVICES_FILE_PATH = 'data/mts_services.json'
REGIONS_FILE_PATH = 'data/russia_subjects.json'

def file_to_json(file_name):
    with open(file_name, encoding='utf-8') as file:
        raw = file.read()
        res = json.loads(raw)
        return res


class MobileOperatorSimulator:
    def __init__(self, metadata):
        self.metadata = metadata
        self.db1_engine = create_engine('sqlite:///:memory:', pool_size=POOL_SIZE, echo=True)
        self.db2_engine = None

        self.generate_schema(self.db1_engine)
        # self.generate_schema(self.db2_engine)

        self.db1_session = scoped_session(sessionmaker(bind=self.db1_engine))
        # self.db2_session = scoped_session(sessionmaker(bind=self.db2_engine))

        self.initial_balance = 200
        # self.initial_fill()

    def generate_schema(self, engine):
        self.metadata.create_all(engine)

    def generate_agreements(self):
        terms_count = 5

        individual_terms = [TermOrCondition(description=random_string().capitalize())
                            for _ in range(terms_count)]
        individual_agreement = Agreement(destination='individual',
                                         terms_and_conditions=individual_terms)

        organization_terms = [TermOrCondition(description=random_string().capitalize())
                              for _ in range(terms_count)]
        organization_agreement = Agreement(destination='organization',
                                           terms_and_conditions=organization_terms)

        self.db1_session.add_all([individual_agreement, organization_agreement])
        self.db1_session.commit()

    def generate_countries(self):
        countries_info = file_to_json(COUNTRIES_FILE_PATH)

        for c_info in countries_info:
            try:
                country_name = c_info['name']
            except UnicodeEncodeError:
                print("EXCEPTION!!!!!!!!!!!!!!!!!!!!!")
                if len(c_info['altSpellings']) > 1:
                    country_name = c_info['altSpellings'][1]
                else:
                    country_name = c_info['altSpellings'][0]

            country = Country(name=country_name,
                              iso2_code=c_info['alpha2Code'],
                              iso3_code=c_info['alpha3Code'])
            # try:
            #     capital_name = c_info['capital'].encode('utf-8')
            #     capital = Place(name=capital_name, capital_of=country)
            # except UnicodeEncodeError:
            #     capital_name = c_info['capital'].encode('latin-1').decode('utf-8')
            #     capital = Place(name=capital_name, capital_of=country)

            #self.db1_session.add_all([country, capital])
            try:
                self.db1_session.add(country)
            except:
                print("ACHTUNG!!!!!!!!!!!!!!!")

        self.db1_session.commit()

    def generate_russian_regions(self):
        regions_info = file_to_json(REGIONS_FILE_PATH)
        subject_types = {
            'Респ': 'republic',
            'обл': 'oblast',
            'г': 'city',
            'край': 'krai',
            'АО': 'autonomous oblast/okrug'
        }
        russia = self.db1_session.query(Country).filter_by(name='Russia').one()

        for r_info in regions_info:
            name = r_info['name']
            code = r_info['regioncode']
            name_tokens = name.split()
            try:
                region_type = subject_types[name_tokens[-1]]
                result_name = translit(' '.join(name_tokens[:-1]), 'ru', reversed=True)
            except:
                region_type = 'unknown'
                result_name = translit(name, 'ru', reversed=True)
            r = Region(name=result_name, type=region_type, code=code, country=russia)
            self.db1_session.add(r)

        self.db1_session.commit()

    def generate_mobile_operators(self):
        operators_info = file_to_json(OPERATORS_FILE_PATH)

        russia = self.db1_session.query(Country).filter_by(name='Russia').one()

        for o_info in operators_info:
            operator_name = o_info['name']
            operator_countries = o_info['countries']
            for country_name in operator_countries:
                if country_name == 'Russia':
                    regions = self.db1_session.query(Region).filter_by(country=russia).all()
                    for region in regions:
                        operator = MobileOperator(name=operator_name, country=russia, region=region)
                        self.db1_session.add(operator)
                else:
                    country = self.db1_session.query(Country).filter_by(name=country_name).one()
                    operator = MobileOperator(name=operator_name, country=country)
                    self.db1_session.add(operator)

        self.db1_session.commit()

    def parse_regional_costs(self, home_operator, target_operators, info):
        costs = []

        home_region = home_operator.region
        home_country = home_operator.country

        used_regions = []
        region_infos = []
        for region in sorted(info, key=lambda region: region['name']):
            region_name = region['name']
            cost = region['cost']
            if region_name == 'HOME_REGION':
                used_regions.append(home_region.name)
                #region_info = {'region': }
            elif region_name == '|REST_REGIONS|':
                rest_regions = self.db1_session.query(Region).\
                    filter(and_(~Region.name.in_(used_regions)),
                                 Region.country == home_country).all()
                del info[region]
                for region_record in rest_regions:
                    region_info = {'name': region_record.name, 'cost': cost}
                    info.append(region_info)
            else:  # Concrete region name
                used_regions.append(region_name)

            # TODO: Incomplete

    def preprocessed_tariffs_countries(self, tariffs_info):
        home_country = 'Russia'
        cis_country_names = set(file_to_json('data/cis_countries.json'))
        europe_country_names = set(file_to_json('data/europe_countries.json'))

        for t_info in tariffs_info:
            for version in t_info['regional_versions']:
                home_region_name = version['region_name']

                for service_info in version['basic_services']:
                    if 'countries' in service_info:
                        used_countries = []
                        new_country_infos = []
                        to_delete = []
                        for country_info in sorted(service_info['countries'],
                                                   key=lambda country: country['name']):
                            country_name = country_info['name']
                            if country_name == 'HOME_COUNTRY':
                                country_info['name'] = home_country
                                used_countries.append(home_country)
                            elif country_name == 'CIS_COUNTRIES':
                                to_delete.append('CIS_COUNTRIES')
                                cost = country_info['cost']
                                for name in cis_country_names - {home_country}:
                                    info = {'name': name, 'cost': cost}
                                    if 'regions' in country_info:
                                        info['regions'] = country_info['regions'][:]
                                    new_country_infos.append(info)
                            elif country_name == 'EUROPE_COUNTRIES':
                                to_delete.append('EUROPE_COUNTRIES')
                                cost = country_info['cost']
                                for name in europe_country_names:
                                    info = {'name': name, 'cost': cost}
                                    new_country_infos.append(info)
                            elif country_name == '|REST_COUNTRIES|':
                                to_delete.append('|REST_COUNTRIES|')
                                cost = country_info['cost']
                                rest_countries = self.db1_session.query(Country).\
                                    filter(~Country.name.in_(used_countries)).all()
                                for country in rest_countries:
                                    info = {'name': country.name, 'cost': cost}
                                    print(info)
                                    if 'regions' in country_info:
                                        info['regions'] = country_info['regions'][:]
                                    new_country_infos.append(info)
                            else:
                                used_countries.append(country_name)
                        #print(to_delete)
                        # Deleting macros
                        #for macro in to_delete:
                        #    service_info['countries'].remove(macro)

                        # Inserting new countries
                        for info in new_country_infos:
                            service_info['countries'].append(info)

        return tariffs_info

    def preprocessed_tariffs_info(self):
        tariffs_info = file_to_json(TARIFFS_FILE_PATH)
        tariffs_info = self.preprocessed_tariffs_countries(tariffs_info)
        return tariffs_info

    def foo(self):
        from preprocessor import TariffPreprocessor

        tariffs_info = file_to_json(TARIFFS_FILE_PATH)
        preprocessor = TariffPreprocessor(tariffs_info, self.db1_session)
        preprocessor.preprocessed()

    def generate_tariffs(self):
        tariffs_info = file_to_json(TARIFFS_FILE_PATH)

        russia = self.db1_session.query(Country).filter_by(name='Russia').one()

        for t_info in tariffs_info:
            tariff_name = t_info['name']
            activation_code = t_info['activation_code']

            for version in t_info['regional_versions']:
                region_name = version['region_name']

                region = self.db1_session.query(Region).filter_by(name=region_name).one()
                regional_operator = self.db1_session.query(MobileOperator).\
                                     filter_by(name='MTS', country=russia, region=region).one()

                tariff = Tariff(name=tariff_name,
                                activation_code=activation_code,
                                operator=regional_operator)

                for service_info in version['basic_services']:
                    service_name = service_info['type']

                    if 'countries' in service_info:
                        pass
                    else:
                        use_cost = service_info['cost']
                        cost = Cost(use_cost=use_cost,
                                    operator_from=regional_operator)
                        service = Service(name=service_name,
                                          operator=regional_operator,
                                          costs=[cost])
                        tariff.attached_services.append(service)

                self.db1_session.add(tariff)

        self.db1_session.commit()

    # def generate_tariffs(self):
    #     tariffs_info = file_to_json(TARIFFS_FILE_PATH)
    #
    #     russia = self.db1_session.query(Country).filter_by(name='Russia').one()
    #
    #     cis_country_names = set(file_to_json('data/cis_countries.json'))
    #     europe_country_names = set(file_to_json('data/europe_countries.json'))
    #
    #     for t_info in tariffs_info:
    #         tariff_name = t_info['name']
    #         activation_code = t_info['activation_code']
    #
    #         for t_region_info in t_info['regional_prices']:
    #             t_region_name = t_region_info['name']
    #             t_basic_services = t_region_info['basic_services']
    #
    #             region = self.db1_session.query(Region).filter_by(name=t_region_name).one()
    #             regional_operator = self.db1_session.query(MobileOperator).\
    #                                 filter_by(name='MTS', country=russia, region=region).one()
    #
    #             t = Tariff(name=tariff_name,
    #                        activation_code=activation_code,
    #                        operator=regional_operator)
    #
    #             for service_info in t_basic_services:
    #                 type = service_info['type']
    #                 service = Service(name=tariff_name + ' - ' + type, operator=regional_operator)
    #
    #                 if 'countries' in service_info:
    #                     country_infos = service_info['countries']
    #                     for country_info in country_infos:
    #                         country_name = country_info['name']
    #
    #                         if country_name == 'CIS_COUNTRIES':
    #                             pass
    #                         elif country_name == 'EUROPE_COUNTRIES':
    #                             pass
    #                         elif country_name == 'REST_COUNTRIES':
    #                             pass
    #                         else:
    #                             country = self.db1_session.query(Country).filter_by(name=country_name)
    #
    #                         if 'operators' in country_info:
    #                             operator_infos = country_info['operators']
    #                             for operator_info in operator_infos:
    #                                 operator_name = operator_info['name']
    #
    #                                 if 'regions' in operator_info:
    #                                     region_infos = operator_info['regions']
    #                                     for region_info in region_infos:
    #                                         region_name = region_info['name']
    #
    #                                         if region_name == 'HOME_REGION':
    #                                             pass
    #                                         elif region_name == 'REST_REGIONS':
    #                                             pass
    #                                         else:
    #                                             pass
    #                                 else:
    #                                     pass
    #                         else:
    #                             mobile_operators = self.db1_session.query(MobileOperator).\
    #                                                filter_by(country=country).all()
    #                             for operator in mobile_operators:
    #                                 pass
    #                 else:
    #                     pass
    #
    #                 t.attached_services.append(service)
    #
    #     self.db1_session.commit()

    def generate_services(self):
        services_info = file_to_json(SERVICES_FILE_PATH)

        russia = self.db1_session.query(Country).filter_by(name='Russia').one()

        for s_info in services_info:
            name = s_info['name']
            activation_code = s_info['name']
            is_periodic = s_info['name']
            if 'regional_versions' in s_info:
                for version in s_info['regional_versions']:
                    region_name = version['region_name']
                    region = self.db1_session.query(Region).filter_by(name=region_name).one()
                    regional_operator = self.db1_session.query(MobileOperator).\
                                        filter_by(name='MTS', country=russia, region=region).one()
                    use_cost = 0.0
                    subscription_cost = 0.0
                    if is_periodic:
                        subscription_cost = version['cost']
                    else:
                        use_cost = version['cost']
                    cost = Cost(operator_from=regional_operator,
                                use_cost=use_cost,
                                subscription_cost=subscription_cost)
                    service = Service(name=name, operator=regional_operator,
                                      activation_code=activation_code, costs=[cost])

                    if 'packet' in version:
                        packet_info = version['packet']
                        packet_type = packet_info['type']
                        amount = packet_info['amount']
                        packet = Packet(type=packet_type, amount=amount)
                        service.packet = packet
                        self.db1_session.add(packet)

                    self.db1_session.add_all([cost, service])

    def generate_calc_methods(self):
        advance = CalculationMethod(type='advance')
        credit = CalculationMethod(type='credit')

        self.db1_session.add_all([advance, credit])
        self.db1_session.commit()

    def initial_fill(self):
        self.generate_agreements()
        self.generate_calc_methods()
        self.generate_countries()
        self.generate_russian_regions()
        self.generate_mobile_operators()
        self.generate_services()
        self.generate_tariffs()


class SimulatedCustomer:
    def __init__(self, customer, behavior_info):
        self.customer = customer

    def sign_agreement(self):
        if self.customer.type == 'individual':
            pass
        else:
            pass

    def register_account(self, agreement):
        pass

    def add_device(self, account):
        pass

    def change_tariff(self, device, new_tariff_name):
        pass

    def activate_service(self, device, service_name):
        pass

    def deactivate_service(self):
        pass

    def connect_service(self):
        pass

    def make_call(self):
        pass

    def use_internet(self):
        pass

    def fill_up_balance(self):
        pass

    def request_billing_history(self):
        pass

    def begin_simulation(self):
        pass

    def simulate_day(self):
        pass


def main():
    sim = MobileOperatorSimulator(Base.metadata)
    sim.initial_fill()
    sim.foo()
    # foo = sim.preprocessed_tariffs_info()
    # with open('data/preprocessed_tariffs.json', 'w') as file:
    #     file.write(json.dumps(foo))

if __name__ == '__main__':
    main()