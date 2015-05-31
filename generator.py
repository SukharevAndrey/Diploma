from datetime import datetime, timedelta

import numpy as np

from transliterate import translit

from actions import Call, IntersectionError
from entities.customer import *
from entities.location import *
from entities.operator import *
from entities.service import *
from entities.payment import *
from tools import file_to_json
from random_data import *
from preprocessor import TariffPreprocessor

COUNTRIES_FILE_PATH = 'data/countries.json'
OPERATORS_FILE_PATH = 'data/operators.json'
TARIFFS_FILE_PATH = 'data/mts_tariffs.json'
SERVICES_FILE_PATH = 'data/mts_services.json'
REGIONS_FILE_PATH = 'data/russia_subjects.json'


class MobileOperatorGenerator:
    def __init__(self, verbose=False):
        self.verbose = verbose

    def print_status(self, status):
        if self.verbose:
            print(status)

    def generate_agreements(self, session):
        self.print_status('Generating agreements...')

        terms_count = 5

        individual_terms = [TermOrCondition(description=random_string().capitalize())
                            for _ in range(terms_count)]
        individual_agreement = Agreement(destination='individual',
                                         terms_and_conditions=individual_terms)

        organization_terms = [TermOrCondition(description=random_string().capitalize())
                              for _ in range(terms_count)]
        organization_agreement = Agreement(destination='organization',
                                           terms_and_conditions=organization_terms)

        session.add_all([individual_agreement, organization_agreement])
        session.commit()

        self.print_status('Done')

    def generate_calc_methods(self, session):
        self.print_status('Generating calculation methods...')

        advance = CalculationMethod(type='advance')
        credit = CalculationMethod(type='credit')

        session.add_all([advance, credit])
        session.commit()

        self.print_status('Done')

    def generate_countries(self, session):
        self.print_status('Generating countries...')

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
            # FIXME: Encodings
            # try:
            #     capital_name = c_info['capital'].encode('utf-8')
            #     capital = Place(name=capital_name, capital_of=country)
            # except UnicodeEncodeError:
            #     capital_name = c_info['capital'].encode('latin-1').decode('utf-8')
            #     capital = Place(name=capital_name, capital_of=country)

            # session.add_all([country, capital])
            try:
                session.add(country)
            except:
                print("ACHTUNG!!!!!!!!!!!!!!!")

        session.commit()

        self.print_status('Done')

    def generate_russian_regions(self, session):
        self.print_status('Generating regions...')
        regions_info = file_to_json(REGIONS_FILE_PATH)
        subject_types = {
            'Респ': 'republic',
            'обл': 'oblast',
            'г': 'city',
            'край': 'krai',
            'АО': 'autonomous oblast/okrug'
        }
        russia = session.query(Country).filter_by(name='Russia').one()

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
            session.add(r)

        session.commit()
        self.print_status('Done')

    def generate_mobile_operators(self, session):
        self.print_status('Generating mobile operators...')
        operators_info = file_to_json(OPERATORS_FILE_PATH)

        russia = session.query(Country).filter_by(name='Russia').one()

        for o_info in operators_info:
            operator_name = o_info['name']
            operator_countries = o_info['countries']
            for country_name in operator_countries:
                if country_name == 'Russia':
                    regions = session.query(Region).filter_by(country=russia).all()
                    for region in regions:
                        operator = MobileOperator(name=operator_name, country=russia, region=region)
                        session.add(operator)
                else:
                    country = session.query(Country).filter_by(name=country_name).one()
                    operator = MobileOperator(name=operator_name, country=country)
                    session.add(operator)

        session.commit()
        self.print_status('Done')

    def generate_services(self, session):
        self.print_status('Generating services...')
        services_info = file_to_json(SERVICES_FILE_PATH)

        russia = session.query(Country).filter_by(name='Russia').one()

        for s_info in services_info:
            name = s_info['name']
            activation_code = s_info['activation_code']
            if 'activation_cost' in s_info:
                activation_cost = s_info['activation_cost']  # TODO: Handle this
            is_periodic = s_info['is_periodic']
            if 'regional_versions' in s_info:
                for version in s_info['regional_versions']:
                    region_name = version['region_name']
                    region = session.query(Region).filter_by(name=region_name).one()
                    regional_operator = session.query(MobileOperator).\
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
                        session.add(packet)

                    session.add_all([cost, service])
            else:
                service = Service(name=name, activation_code=activation_code)
                session.add(service)

        session.commit()
        self.print_status('Done')

    def generate_tariffs(self, session):
        self.print_status('Generating tariffs...')
        tariffs_info = file_to_json(TARIFFS_FILE_PATH)
        preprocessor = TariffPreprocessor(session)
        preprocessor.preprocess(tariffs_info, replace=True)

        for tariff_info in tariffs_info:
            tariff_name = tariff_info['name']
            activation_code = tariff_info['activation_code']

            for regional_version in tariff_info['regional_versions']:
                home_region_name = regional_version['region_name']
                home_country_name = regional_version['country_name']
                transition_cost = regional_version['transition_cost']
                subscription_cost = regional_version['subscription_cost']

                home_country = session.query(Country).filter_by(name=home_country_name).one()
                home_region = session.query(Region).filter_by(name=home_region_name).one()
                regional_operator = session.query(MobileOperator).\
                    filter_by(name='MTS', country=home_country, region=home_region).one()

                tariff = Tariff(name=tariff_name,
                                activation_code=activation_code,
                                activation_cost=transition_cost,
                                operator=regional_operator)

                cost = Cost(operator_from=regional_operator,
                            subscription_cost=subscription_cost)
                tariff.costs.append(cost)

                # Adding basic services such as calls, sms, etc...
                for service_info in regional_version['basic_services']:
                    service_name = service_info['type']
                    service = Service(name=service_name,
                                      operator=regional_operator)

                    if 'countries' in service_info:
                        # We have specified countries with own pricing
                        for country_info in service_info['countries']:
                            country_name = country_info['name']
                            country = session.query(Country).filter_by(name=country_name).one()

                            if 'operators' in country_info:
                                for operator_info in country_info['operators']:
                                    operator_name = operator_info['name']

                                    if 'regions' in operator_info:
                                        for region_info in operator_info['regions']:
                                            region_name = region_info['name']
                                            use_cost = region_info['cost']
                                            region = session.query(Region).\
                                                filter_by(name=region_name, country=country).one()
                                            local_operator = session.query(MobileOperator).\
                                                filter_by(name=operator_name, country=country, region=region).one()
                                            cost = Cost(use_cost=use_cost,
                                                        operator_from=regional_operator,
                                                        operator_to=local_operator)
                                            service.costs.append(cost)
                                    else:
                                        # TODO: Generalize?
                                        use_cost = operator_info['cost']
                                        # Setting cost to all regional operators with that name
                                        operators = session.query(MobileOperator).\
                                            filter_by(name=operator_name, country=country).all()
                                        for operator in operators:
                                            cost = Cost(use_cost=use_cost,
                                                        operator_from=regional_operator,
                                                        operator_to=operator)
                                            service.costs.append(cost)
                            else:
                                use_cost = country_info['cost']
                                operators = session.query(MobileOperator).\
                                    filter_by(country=country).all()
                                for operator in operators:
                                    cost = Cost(use_cost=use_cost,
                                                operator_from=regional_operator,
                                                operator_to=operator)
                                    service.costs.append(cost)
                    else:
                        # We don't have specific countries
                        # TODO: Find all operators in all countries?
                        use_cost = service_info['cost']
                        cost = Cost(use_cost=use_cost,
                                    operator_from=regional_operator)
                        service.costs.append(cost)

                    tariff.attached_services.append(service)

                # Adding included services such as packets
                for service_info in regional_version['services']:
                    service_name = service_info['name']
                    is_periodic = service_info['is_periodic']
                    s_cost = service_info['cost']

                    service = Service(name=service_name,
                                      operator=regional_operator)
                    if is_periodic:
                        cost = Cost(operator_from=regional_operator,
                                    use_cost=s_cost)
                    else:
                        cost = Cost(operator_from=regional_operator,
                                    subscription_cost=s_cost)
                    service.costs.append(cost)

                    if 'packet' in service_info:
                        packet_info = service_info['packet']
                        packet = Packet(type=packet_info['type'],
                                        amount=packet_info['amount'])
                        service.packet = packet

                    if 'restrictions' in service_info:
                        # TODO: Add restrictions
                        pass

                    tariff.attached_services.append(service)

                session.add(tariff)

        session.commit()
        self.print_status('Done')

    def generate_payment_methods(self, session):
        self.print_status('Generating payment methods...')
        cash = Cash()

        # TODO: All third party payments from jsom
        qiwi = ThirdPartyCollection(name='QIWI')
        yandex = ThirdPartyCollection(name='Yandex.Money')
        webmoney = ThirdPartyCollection(name='WebMoney')

        session.add_all([cash, qiwi, yandex, webmoney])
        session.commit()
        self.print_status('Done')

    def generate_static_data(self, session):
        self.generate_agreements(session)
        self.generate_calc_methods(session)
        self.generate_payment_methods(session)
        self.generate_countries(session)
        self.generate_russian_regions(session)
        self.generate_mobile_operators(session)
        self.generate_services(session)
        self.generate_tariffs(session)

class Distribution:
    def __init__(self, values_count, probabilities):
        self.values_count = values_count
        self.values = [i for i in range(1, values_count+1)]
        self.p = np.array(probabilities)
        if len(probabilities) < values_count:
            self.p = np.concatenate((self.p, np.zeros(values_count-len(probabilities))))

        self.normalize()

    def normalize(self):
        sum_p = np.sum(self.p)
        self.p /= sum_p

    def get_value(self):
        return np.random.choice(self.values, p=self.p)

class TimeLineGenerator:
    MINUTES_IN_DAY = 1440
    HOURS_IN_DAY = 24
    MINUTES_IN_HOUR = 60
    SECONDS_IN_MINUTE = 60

    DISTRIBUTIONS_FILE = 'data/distributions.json'

    months = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }

    def __init__(self, customer, device):
        self.customer = customer
        self.device = device

    def minutes_to_time(self, minute):
        return divmod(minute, self.MINUTES_IN_HOUR)

    def generate_timeline(self, date):
        return self.generate_calls(date, 10)

    def generate_calls(self, date, amount):
        start_times = self.get_start_times(date=date, amount=amount)
        calls = []
        for i in range(amount-1):
            start_time = start_times[i]
            next_start_time = start_times[i+1]
            delta = next_start_time-start_time
            call = Call(self.customer, self.device, start_time, delta)
            self.gen_call_duration(call)
            calls.append(call)
        return calls

    def gen_call_duration(self, call):
        while True:
            duration_minutes = np.random.randint(0, 30)
            duration_seconds = np.random.randint(0, 59)
            duration = timedelta(minutes=duration_minutes, seconds=duration_seconds)
            try:
                call.duration = duration
            except IntersectionError:
                continue
            return

    def get_start_times(self, date, amount, can_overlap=False):
        year, month, day = date
        times = []
        hm = np.random.randint(0, self.MINUTES_IN_DAY, amount)
        seconds = np.random.randint(0, self.SECONDS_IN_MINUTE, amount)
        for i in range(amount):
            hour, minute = self.minutes_to_time(hm[i])
            second = seconds[i]
            times.append(datetime(year, month, day, hour, minute, second))
        times.sort()
        return times
