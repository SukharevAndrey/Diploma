from datetime import datetime
from collections import Counter

import numpy as np
from transliterate import translit

from actions import *
from distribution import Distribution
from entities.customer import *
from entities.location import *
from entities.operator import *
from entities.service import *
from entities.payment import *
from tools import file_to_json, distribution_from_list
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
            has_regions = o_info['has_regions']

            for country_name in operator_countries:
                if country_name == 'Russia':
                    if has_regions:
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
                activation_cost = s_info['activation_cost']
            else:
                activation_cost = 0
            is_periodic = s_info['is_periodic']

            if 'duration_days' in s_info:
                duration_days = s_info['duration_days']
            else:
                duration_days = 0

            if 'regional_versions' in s_info:
                for version in s_info['regional_versions']:
                    region_name = version['region_name']
                    region = session.query(Region).filter_by(name=region_name).one()
                    regional_operator = session.query(MobileOperator).\
                        filter_by(name='MTS', country=russia, region=region).one()

                    if is_periodic:
                        cost = Cost(operator_from=regional_operator,
                                    subscription_cost=version['cost'])
                    else:
                        cost = Cost(operator_from=regional_operator,
                                    use_cost=version['cost'])

                    service = Service(name=name, operator=regional_operator,
                                      activation_code=activation_code, duration_days=duration_days,
                                      activation_cost=activation_cost, costs=[cost])

                    if 'packet' in version:
                        packet_info = version['packet']
                        packet = Packet(type=packet_info['type'], amount=packet_info['amount'])
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
                                duration_days=30,
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
                            # TODO: Optimize country queries
                            country_name = country_info['name']
                            country = session.query(Country).filter_by(name=country_name).one()

                            if 'operators' in country_info:
                                for operator_info in country_info['operators']:
                                    operator_name = operator_info['name']

                                    if 'regions' in operator_info:
                                        local_operators = session.query(MobileOperator).\
                                            filter_by(name=operator_name, country=country).all()
                                        regions = session.query(Region).filter_by(country=country).all()

                                        region_name_cost = {}
                                        for region_info in operator_info['regions']:
                                            region_name = region_info['name']
                                            use_cost = region_info['cost']
                                            region_name_cost[region_name] = use_cost

                                        region_cost = {}
                                        for region in regions:
                                            region_cost[region] = region_name_cost[region.name]

                                        for local_operator in local_operators:
                                            use_cost = region_cost[local_operator.region]
                                            cost = Cost(use_cost=use_cost,
                                                        operator_from=regional_operator,
                                                        operator_to=local_operator)
                                            service.costs.append(cost)
                                    else:
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
                        use_cost = service_info['cost']
                        cost = Cost(use_cost=use_cost,
                                    operator_from=regional_operator)
                        service.costs.append(cost)

                    tariff.attached_services.append(service)

                # Adding included services such as packets
                # TODO: Merge with services generation
                for service_info in regional_version['services']:
                    service_name = service_info['name']
                    is_periodic = service_info['is_periodic']
                    s_cost = service_info['cost']
                    if 'duration_days' in service_info:
                        duration_days = service_info['duration_days']
                    else:
                        duration_days = 0

                    if is_periodic:
                        cost = Cost(operator_from=regional_operator,
                                    use_cost=s_cost)
                    else:
                        cost = Cost(operator_from=regional_operator,
                                    subscription_cost=s_cost)

                    service = Service(name=service_name,
                                      operator=regional_operator,
                                      duration_days=duration_days,
                                      costs=[cost])

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
        cash = Cash(name='Cash')

        # TODO: All third party payments from json
        qiwi = ThirdPartyCollection(name='QIWI')
        yandex = ThirdPartyCollection(name='Yandex.Money')
        webmoney = ThirdPartyCollection(name='WebMoney')

        session.add_all([cash, qiwi, yandex, webmoney])
        session.commit()
        self.print_status('Done')

    def generate_fake_phone_numbers(self, session):
        self.print_status('Generating fake phone numbers for each operator')

        mobile_operators = session.query(MobileOperator).all()
        n = len(mobile_operators)
        print('There are %d mobile operators' % n)

        customers_amount = 10
        area_code = 999
        next_number = 0

        for operator in mobile_operators:
            phone_numbers = []

            for i in range(customers_amount):
                phone_number = PhoneNumber(mobile_operator_id=operator.id,
                                           area_code=area_code, number=str(next_number).zfill(7))
                phone_numbers.append(phone_number)
                next_number += 1

            session.bulk_save_objects(phone_numbers)
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
        self.generate_fake_phone_numbers(session)


DISTRIBUTIONS_FILE = 'data/distributions.json'
distributions_info = file_to_json(DISTRIBUTIONS_FILE)

class TimeLineGenerator:
    PERIOD_DURATION = 30
    MINUTES_IN_DAY = 1440
    HOURS_IN_DAY = 24
    MINUTES_IN_HOUR = 60
    SECONDS_IN_MINUTE = 60

    russian_regions = ['Moskva', 'Brjanskaja', 'Leningradskaja']  # TODO: Full regions list

    action_match = {
        'Call': Call, 'SMS': SMS, 'MMS': MMS, 'Internet': Internet
    }

    basic_services = {'Call', 'Internet', 'SMS', 'MMS'}
    other_activities = {'Payment', 'Traveling', 'Tariff changing'}

    def __init__(self, customer, device, period_start_date):
        self.sim_customer = customer
        self.sim_device = device
        self.period_start_date = period_start_date
        self.service_info = {}

        self.days_distribution = {}
        self.duration_distribution = {}

        self.parse_activity()

    def get_start_times(self, date, amount):
        year, month, day = date.year, date.month, date.day
        times = []
        # TODO: Get from service distribution times
        hm = np.random.randint(0, self.MINUTES_IN_DAY, amount)
        seconds = np.random.randint(0, self.SECONDS_IN_MINUTE, amount)
        for i in range(amount):
            hour, minute = self.minutes_to_time(hm[i])
            second = seconds[i]
            times.append(datetime(year, month, day, hour, minute, second))

        return times

    def parse_activity(self):
        basic_services_info = self.sim_device.behavior_info['Basic services']
        other_services_info = self.sim_device.behavior_info['Other services']
        other_activity_info = self.sim_device.behavior_info['Other activity']

        for service_name in basic_services_info:
            service_info = basic_services_info[service_name]
            self.service_info[service_name] = service_info
            service_activity = service_info['period_activity']
            day_distribution_info = distributions_info['month'][service_activity['days_activity']]
            self.days_distribution[service_name] = Distribution(info=day_distribution_info)
            if 'duration' in service_activity:
                dur_distribution_info = distributions_info['duration'][service_activity['duration']]
                self.duration_distribution[service_name] = Distribution(info=dur_distribution_info)

        for service_name in other_services_info:
            # Writing service info
            service_info = other_services_info[service_name]
            self.service_info[service_name] = service_info

            # Creating distribution
            service_activity = service_info['period_activity']
            day_distribution_info = distributions_info['month'][service_activity['days_activity']]
            self.days_distribution[service_name] = Distribution(info=day_distribution_info)

        for activity_name in other_activity_info:
            activity_info = other_activity_info[activity_name]
            self.service_info[activity_name] = activity_info

            period_activity = activity_info['period_activity']
            day_distribution_info = distributions_info['month'][period_activity['days_activity']]
            self.days_distribution[activity_name] = Distribution(info=day_distribution_info)

    def minutes_to_time(self, minute):
        return divmod(minute, self.MINUTES_IN_HOUR)

    def generate_timeline(self, date):
        actions = []
        actions.extend(self.generate_basic_services(date))
        actions.extend(self.generate_other_services(date))
        actions.extend(self.generate_tariff_changes(date))
        actions.extend(self.generate_location_changes(date))
        actions.extend(self.generate_payments(date))

        actions.sort(key=lambda action: action.start_date)
        return actions

    def get_day_in_period(self, date):
        return (date-self.period_start_date).days % self.PERIOD_DURATION + 1

    def get_service_amount_for_period(self, service_name):
        period_activity = self.service_info[service_name]['period_activity']
        avg_amount = period_activity['amount']
        max_deviation = period_activity['max_deviation']

        lower_boundary = max(0, avg_amount-max_deviation)
        higher_boundary = avg_amount+max_deviation

        if higher_boundary < lower_boundary:
            lower_boundary, higher_boundary = higher_boundary, lower_boundary

        if lower_boundary == higher_boundary:
            total_period_service = lower_boundary
        else:
            total_period_service = np.random.randint(lower_boundary, higher_boundary)
        period_usage_days = self.days_distribution[service_name].get_value(n=total_period_service)

        return Counter(period_usage_days)

    def generate_basic_services(self, date):
        all_service_usages = []

        for service_name in {'Call', 'SMS', 'MMS', 'Internet'}:
            # print('Generating %s actions' % service_name)
            service_usages = []

            service_days = self.get_service_amount_for_period(service_name)
            day_in_period = self.get_day_in_period(date)
            amount = service_days[day_in_period]

            start_times = self.get_start_times(date=date, amount=amount)
            action_entity = self.action_match[service_name]
            if service_name == 'Call':
                start_times.sort()
                deltas = [start_times[i+1]-start_times[i] for i in range(amount-1)] + [None]

            if service_name in ('Call', 'Internet'):
                duration_distribution = self.duration_distribution[service_name]

            recipient_info = {'operator': {  # TODO: Real generation
                'name': 'MTS',
                'country': 'Russia',
                'region': 'Moskva'
            },
                'phone_number': {
                    'code': '916',
                    'number': '7654321',
                }}

            for i in range(amount):
                if service_name == 'Call':
                    # TODO: May overlap if conference
                    service = action_entity(self.sim_device, start_times[i], deltas[i], can_overlap=False)
                    service.generate_duration(duration_distribution)
                    service.recipient_info = recipient_info
                elif service_name == 'Internet':
                    service = action_entity(self.sim_device, start_times[i])
                    service.generate_service_usage(duration_distribution)
                else:
                    service = action_entity(self.sim_device, start_times[i])
                    service.recipient_info = recipient_info

                service_usages.append(service)

            all_service_usages.extend(service_usages)
        return all_service_usages

    def generate_other_services(self, date):
        service_usages = []

        for service_name in self.service_info:
            if service_name not in (self.basic_services | self.other_activities):
                # print('Generating %s actions' % service_name)
                info = self.service_info[service_name]
                activation_code = info['activation_code']
                usage_type = info['type']

                service_days = self.get_service_amount_for_period(service_name)
                # print(service_days)
                day_in_period = self.get_day_in_period(date)
                amount = service_days[day_in_period]

                start_times = self.get_start_times(date=date, amount=amount)
                for i in range(amount):
                    service = OneTimeService(self.sim_device, start_times[i], service_name,
                                             activation_code, usage_type)
                    service_usages.append(service)

        return service_usages

    def generate_tariff_changes(self, date):
        # print('Generating tariff changes')
        tariff_changes = []

        info = self.service_info['Tariff changing']
        potential_tariffs = info['tariffs']

        change_days = self.get_service_amount_for_period('Tariff changing')
        day_in_period = self.get_day_in_period(date)
        amount = change_days[day_in_period]

        start_times = self.get_start_times(date=date, amount=amount)
        new_tariffs = [random.choice(potential_tariffs) for _ in range(amount)]
        smart_mini_info = {'name': 'Smart mini', 'code': '*100*1#'}
        for i in range(amount):
            tariff_info = new_tariffs[i]
            # FIXME: Delete after adding other tariffs
            if tariff_info['name'] != 'Smart mini':
                tariff_info = smart_mini_info
            change = TariffChange(self.sim_device, start_times[i], tariff_info['code'], tariff_info['name'])
            tariff_changes.append(change)

        return tariff_changes

    def get_location_from_macro(self, macro):
        # TODO: Full country lists
        home_location = self.sim_device.home_region
        if macro == 'HOME_COUNTRY_REGION':
            if home_location['country'] == 'Russia':
                return {'country': 'Russia', 'region': random.choice(self.russian_regions)}
            else:
                return {'country': home_location['country'], 'region': 'None'}
        elif macro == 'CIS_COUNTRY':
            return {'country': 'Ukraine', 'region': None}
        elif macro == 'EUROPE_COUNTRY':
            return {'country': 'Germany', 'region': None}
        else:
            return {'country': 'United States', 'region': None}

    def generate_location_changes(self, date):
        # print('Generating location changes')
        location_changes = []

        info = self.service_info['Traveling']
        destinations = info['destinations']

        travel_days = self.get_service_amount_for_period('Traveling')
        day_in_period = self.get_day_in_period(date)
        amount = travel_days[day_in_period]

        start_times = self.get_start_times(date=date, amount=amount)
        dest_distribution = distribution_from_list(destinations)
        new_location_macroses = dest_distribution.get_value(n=amount)
        for i in range(amount):
            change = LocationChange(self.sim_device, start_times[i], self.get_location_from_macro(new_location_macroses[i]))
            location_changes.append(change)

        return location_changes

    def generate_payments(self, date):
        # print('Generating payments')
        payments = []

        info = self.service_info['Payment']
        methods = info['methods']
        sums = info['sums']
        method_distribution = distribution_from_list(methods)
        sum_distribution = distribution_from_list(sums)

        payment_days = self.get_service_amount_for_period('Payment')
        day_in_period = self.get_day_in_period(date)
        amount = payment_days[day_in_period]

        start_times = self.get_start_times(date=date, amount=amount)
        for i in range(amount):
            method = method_distribution.get_value(return_array=False).copy()
            method_name, method_type = method.popitem()
            payment_sum = int(sum_distribution.get_value(return_array=False))  # TODO: Decimal?
            payment = DevicePayment(self.sim_device, start_times[i], method_name, method_type, payment_sum)
            payments.append(payment)

        return payments
