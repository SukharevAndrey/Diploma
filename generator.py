from datetime import datetime
from collections import Counter
from decimal import Decimal

import numpy as np
from transliterate import translit

from actions import *
from distribution import Distribution
from entities.customer import *
from entities.location import *
from entities.operator import *
from entities.service import *
from entities.payment import *
from tools import distribution_from_list
from random_data import *
from preprocessor import TariffPreprocessor
from file_info import distributions_info, countries_info, regions_info,\
    operators_info, tariffs_info, services_info, out_of_funds_info


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

        self.print_status('Done')

    def generate_calc_methods(self, session):
        self.print_status('Generating calculation methods...')

        advance = CalculationMethod(type='advance')
        credit = CalculationMethod(type='credit')

        session.add_all([advance, credit])

        self.print_status('Done')

    def generate_countries(self, session):
        self.print_status('Generating countries...')

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

        self.print_status('Done')

    def generate_russian_regions(self, session):
        self.print_status('Generating regions...')
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

        self.print_status('Done')

    def generate_mobile_operators(self, session):
        self.print_status('Generating mobile operators...')

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

        self.print_status('Done')

    def generate_services(self, session):
        self.print_status('Generating services...')

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

        self.print_status('Done')

    def generate_tariffs(self, session):
        self.print_status('Generating tariffs...')
        preprocessor = TariffPreprocessor(session)
        preprocessor.preprocess(tariffs_info, replace=True)

        # Caching countries
        countries = session.query(Country).all()
        country_match = {}
        for country in countries:
            country_match[country.name] = country

        for tariff_info in tariffs_info:
            tariff_name = tariff_info['name']
            activation_code = tariff_info['activation_code']

            for regional_version in tariff_info['regional_versions']:
                home_region_name = regional_version['region_name']
                home_country_name = regional_version['country_name']
                transition_cost = regional_version['transition_cost']
                subscription_cost = regional_version['subscription_cost']

                home_country = country_match[home_country_name]
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
                            country = country_match[country_name]

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

        self.print_status('Done')

    def generate_payment_methods(self, session):
        self.print_status('Generating payment methods...')
        cash = Cash(name='Cash')

        # TODO: All third party payments from json
        qiwi = ThirdPartyCollection(name='QIWI')
        yandex = ThirdPartyCollection(name='Yandex.Money')
        webmoney = ThirdPartyCollection(name='WebMoney')

        session.add_all([cash, qiwi, yandex, webmoney])
        # session.commit()
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

        self.print_status('Done')

    def generate_static_data(self, session):
        self.generate_agreements(session)
        self.generate_calc_methods(session)
        self.generate_payment_methods(session)
        self.generate_countries(session)
        session.flush()
        self.generate_russian_regions(session)  # Depend on countries
        session.flush()
        self.generate_mobile_operators(session)  # Depend on countries and regions
        session.flush()
        # Depend on mobile operators
        self.generate_services(session)
        self.generate_tariffs(session)
        self.generate_fake_phone_numbers(session)
        session.commit()


class ActivityGenerator:
    PERIOD_DURATION = 30
    MINUTES_IN_DAY = 1440
    HOURS_IN_DAY = 24
    MINUTES_IN_HOUR = 60
    SECONDS_IN_MINUTE = 60

    def __init__(self, period_start_date):
        self.period_start_date = period_start_date
        self.days_distribution = {}
        self.activity_info = {}

    def parse_activity(self):
        raise NotImplementedError

    def generate_timeline(self, date_from, date_to):
        raise NotImplementedError

    def minutes_to_time(self, minute):
        return divmod(minute, self.MINUTES_IN_HOUR)

    def get_day_in_period(self, date):
        return (date-self.period_start_date).days % self.PERIOD_DURATION + 1

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

    def get_amount_for_period(self, activity_name):
        period_activity = self.activity_info[activity_name]['period_activity']
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
        period_usage_days = self.days_distribution[activity_name].get_value(n=total_period_service)

        return Counter(period_usage_days)


class AccountActivityGenerator(ActivityGenerator):
    def __init__(self, account, period_start_date):
        super().__init__(period_start_date)

        self.sim_account = account
        self.distributions = {}

        self.parse_activity()

    def parse_activity(self):
        self.activity_info = self.sim_account.account_cluster_info['activity']
        payment_activity = self.activity_info['Payment']

        method_distribution = distribution_from_list(distributions_info['method'][payment_activity['methods']])
        self.distributions['method'] = method_distribution
        sum_distribution = distribution_from_list(distributions_info['sum'][payment_activity['sums']])
        self.distributions['sum'] = sum_distribution

        payment_period_activity = payment_activity['period_activity']
        day_distribution_info = distributions_info['month'][payment_period_activity['days_activity']]
        self.days_distribution['Payment'] = Distribution(info=day_distribution_info)

    def generate_timeline(self, date_from, date_to):
        actions = []
        actions.extend(self.generate_payments(date_from, date_to))

        return actions

    def generate_payments(self, date_from, date_to):
        payments = []

        method_distribution = self.distributions['method']
        sum_distribution = self.distributions['sum']

        payment_days = self.get_amount_for_period('Payment')

        cur_date = date_from
        while cur_date <= date_to:
            day_in_period = self.get_day_in_period(cur_date)
            amount = payment_days[day_in_period]
            start_times = self.get_start_times(date=cur_date, amount=amount)

            for i in range(amount):
                method = method_distribution.get_value(return_array=False).copy()
                method_name, method_type = method.popitem()
                payment_sum = int(sum_distribution.get_value(return_array=False))
                payment = AccountPayment(self.sim_account, start_times[i], method_name, method_type, payment_sum)
                payments.append(payment)

            cur_date += timedelta(days=1)

        return payments


class DeviceActivityGenerator(ActivityGenerator):
    russian_regions = ['Moskva', 'Brjanskaja', 'Leningradskaja']  # TODO: Full regions list

    basic_services = {'Call', 'Internet', 'SMS', 'MMS'}
    other_activities = {'Traveling', 'Tariff changing'}

    def __init__(self, device, period_start_date):
        super().__init__(period_start_date)

        self.sim_device = device
        self.duration_distribution = {}
        self.out_of_funds_distributions = {}

        self.parse_activity()

    def parse_activity(self):
        basic_services_info = self.sim_device.behavior_info['Basic services']
        other_services_info = self.sim_device.behavior_info['Other services']
        other_activity_info = self.sim_device.behavior_info['Other activity']

        for service_name in basic_services_info:
            service_info = basic_services_info[service_name]
            self.activity_info[service_name] = service_info

            service_activity = service_info['period_activity']
            day_distribution_info = distributions_info['month'][service_activity['days_activity']]
            self.days_distribution[service_name] = Distribution(info=day_distribution_info)

            if 'duration' in service_activity:
                dur_distribution_info = distributions_info['duration'][service_activity['duration']]
                self.duration_distribution[service_name] = Distribution(info=dur_distribution_info)

        for service_name in other_services_info:
            # Writing service info
            service_info = other_services_info[service_name]
            self.activity_info[service_name] = service_info

            # Creating distribution
            service_activity = service_info['period_activity']
            day_distribution_info = distributions_info['month'][service_activity['days_activity']]
            self.days_distribution[service_name] = Distribution(info=day_distribution_info)

        for activity_name in other_activity_info:
            activity_info = other_activity_info[activity_name]
            self.activity_info[activity_name] = activity_info

            period_activity = activity_info['period_activity']
            day_distribution_info = distributions_info['month'][period_activity['days_activity']]
            self.days_distribution[activity_name] = Distribution(info=day_distribution_info)

        # TODO: Static for all instances
        for category_num in out_of_funds_info['trust_category']:
            category = int(category_num)
            category_activity = out_of_funds_info['trust_category'][category_num]
            self.out_of_funds_distributions[category] = {}
            for action_name in category_activity:
                actions_info = category_activity[action_name]['actions']
                action_distribution = distribution_from_list(actions_info)
                self.out_of_funds_distributions[category][action_name] = action_distribution

    def generate_timeline(self, date_from, date_to):
        actions = []
        actions.extend(self.generate_calls(date_from, date_to))
        actions.extend(self.generate_messages(date_from, date_to))
        actions.extend(self.generate_internet_usages(date_from, date_to))

        actions.extend(self.generate_other_services(date_from, date_to))
        actions.extend(self.generate_tariff_changes(date_from, date_to))
        actions.extend(self.generate_location_changes(date_from, date_to))

        return actions

    def get_recipient(self, distribution=None):
        # TODO: Real recipient generation using distribution
        recipient_info = {'operator': {'name': 'MTS',
                                       'country': 'Russia',
                                       'region': 'Moskva'
                                       },
                          'phone_number': {
                              'code': '916',
                              'number': '7654321',
                          }}
        return recipient_info

    def generate_calls(self, date_from, date_to):
        call_actions = []
        call_day_usages = self.get_amount_for_period('Call')
        call_duration_distribution = self.duration_distribution['Call']
        out_of_funds = self.out_of_funds_distributions[self.sim_device.trust_category]['Call']

        cur_date = date_from
        while cur_date <= date_to:
            day_in_period = self.get_day_in_period(cur_date)
            amount = call_day_usages[day_in_period]

            start_times = self.get_start_times(date=cur_date, amount=amount)
            start_times.sort()
            deltas = [start_times[i+1]-start_times[i] for i in range(amount-1)] + [None]

            for i in range(amount):
                call = Call(self.sim_device, start_times[i], deltas[i],
                            self.get_recipient(None), out_of_funds, can_overlap=False)
                call.generate_duration(call_duration_distribution)
                call_actions.append(call)

            cur_date += timedelta(days=1)

        return call_actions

    def generate_messages(self, date_from, date_to):
        message_actions = []
        out_of_funds = self.out_of_funds_distributions[self.sim_device.trust_category]['Message']

        for service in ('SMS', 'MMS'):
            message_day_usages = self.get_amount_for_period(service)

            cur_date = date_from
            while cur_date <= date_to:
                day_in_period = self.get_day_in_period(cur_date)
                amount = message_day_usages[day_in_period]

                start_times = self.get_start_times(date=cur_date, amount=amount)
                for i in range(amount):
                    message = Message(self.sim_device, start_times[i], service.lower(),
                                      self.get_recipient(None), out_of_funds)
                    message_actions.append(message)

                cur_date += timedelta(days=1)

        return message_actions

    def generate_internet_usages(self, date_from, date_to):
        internet_actions = []
        internet_day_usages = self.get_amount_for_period('Internet')
        session_length_distribution = self.duration_distribution['Internet']
        out_of_funds = self.out_of_funds_distributions[self.sim_device.trust_category]['Internet']

        cur_date = date_from
        while cur_date <= date_to:
            day_in_period = self.get_day_in_period(cur_date)
            amount = internet_day_usages[day_in_period]

            start_times = self.get_start_times(date=cur_date, amount=amount)
            for i in range(amount):
                internet = Internet(self.sim_device, start_times[i], out_of_funds)
                internet.generate_service_usage(session_length_distribution)
                internet_actions.append(internet)

            cur_date += timedelta(days=1)

        return internet_actions

    def generate_other_services(self, date_from, date_to):
        service_usages = []
        # TODO: Out of funds?

        for service_name in self.activity_info:
            if service_name not in (self.basic_services | self.other_activities):
                info = self.activity_info[service_name]
                activation_code = info['activation_code']
                usage_type = info['type']
                service_days = self.get_amount_for_period(service_name)

                cur_date = date_from
                while cur_date <= date_to:
                    day_in_period = self.get_day_in_period(cur_date)
                    amount = service_days[day_in_period]

                    start_times = self.get_start_times(date=cur_date, amount=amount)
                    for i in range(amount):
                        service = OneTimeService(self.sim_device, start_times[i], service_name,
                                                 activation_code, usage_type, None)
                        service_usages.append(service)

                    cur_date += timedelta(days=1)

        return service_usages

    def generate_tariff_changes(self, date_from, date_to):
        tariff_changes = []

        info = self.activity_info['Tariff changing']
        potential_tariffs = info['tariffs']
        change_days = self.get_amount_for_period('Tariff changing')
        out_of_funds = self.out_of_funds_distributions[self.sim_device.trust_category]['TariffChange']

        cur_date = date_from
        while cur_date <= date_to:
            day_in_period = self.get_day_in_period(cur_date)
            amount = change_days[day_in_period]

            start_times = self.get_start_times(date=cur_date, amount=amount)
            new_tariffs = [random.choice(potential_tariffs) for _ in range(amount)]

            for i in range(amount):
                tariff_info = new_tariffs[i]
                # FIXME: Delete after adding other tariffs
                smart_mini_info = {'name': 'Smart mini', 'code': '*111*1023#'}
                if tariff_info['name'] != 'Smart mini':
                    tariff_info = smart_mini_info
                change = TariffChange(self.sim_device, start_times[i], tariff_info['code'], tariff_info['name'],
                                      out_of_funds)
                tariff_changes.append(change)

            cur_date += timedelta(days=1)

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

    def generate_location_changes(self, date_from, date_to):
        location_changes = []

        info = self.activity_info['Traveling']
        destinations = distributions_info['destination'][info['destinations']]
        dest_distribution = distribution_from_list(destinations)
        travel_days = self.get_amount_for_period('Traveling')

        cur_date = date_from
        while cur_date <= date_to:
            day_in_period = self.get_day_in_period(cur_date)
            amount = travel_days[day_in_period]
            start_times = self.get_start_times(date=cur_date, amount=amount)

            new_locations = dest_distribution.get_value(n=amount)
            for i in range(amount):
                change = LocationChange(self.sim_device, start_times[i],
                                        self.get_location_from_macro(new_locations[i]))
                location_changes.append(change)

            cur_date += timedelta(days=1)

        return location_changes
