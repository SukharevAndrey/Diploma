from collections import deque
from decimal import Decimal
from time import time
import logging
import os

from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from entities.customer import *
from entities.location import *
from entities.operator import *
from entities.payment import *
from entities.service import *
from file_info import user_groups_info, agreements_info, accounts_info, devices_info, distributions_info
from generator import MobileOperatorGenerator, AccountActivityGenerator, DeviceActivityGenerator
from distribution import Distribution
from random_data import *
from tools import distribution_from_list
from status import ServiceStatus
from analyzer import ActivityAnalyzer
from loading import LoadSimulator

# TODO: Decimal service amount
# TODO: Global entities cache

logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d.%m.%Y %H:%M:%S',
#                    level=logging.INFO)
#                     level=logging.CRITICAL)
                    filename='activity.log', filemode='w', level=logging.INFO)
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

class MobileOperatorSimulator:
    def __init__(self, metadata):
        self.metadata = metadata
        # TODO: From config
        self.main_engine = create_engine('sqlite:///:memory:')
        self.test_engine = create_engine('sqlite:///:memory:')

        self.generate_schema(self.main_engine)
        self.generate_schema(self.test_engine)

        self.main_session = sessionmaker(bind=self.main_engine)()
        self.main_session.autoflush = False
        self.test_session = sessionmaker(bind=self.test_engine)()
        self.test_session.autoflush = False  # TODO: True?

        self.system = MobileOperatorSystem(self.main_session)
        self.analyzer = ActivityAnalyzer(self.main_session)
        self.load_simulator = LoadSimulator(self.main_session, self.test_session)

        self.customers = []
        self.customer_clusters = {}

    def generate_schema(self, engine):
        self.metadata.create_all(engine, checkfirst=True)

    def generate_customers(self, generation_date):
        print('Generating customers')
        start_time = time()

        for group_name in user_groups_info:
            group_info = user_groups_info[group_name]
            size = group_info['size']
            customer_type = group_info['customer_type']
            age_distribution = Distribution(info=distributions_info['age'][group_info['ages']])
            age = int(age_distribution.get_value(return_array=False))

            for i in range(size):
                if customer_type == 'individual':
                    customer = random_individual(generation_date, age)
                else:
                    customer = random_organization(generation_date)

                customer.cluster_id = group_info['cluster_id']
                c = SimulatedCustomer(customer, group_info['agreements'], self.main_session, self.system, verbose=True)
                c.generate_hierarchy(generation_date)
                self.customers.append(c)

        self.main_session.commit()
        end_time = time()
        print('Customers generation done in %f seconds' % (end_time-start_time))

    def simulate_period(self, date_from, date_to):
        print('Simulating customers activity from %s to %s' % (date_from, date_to))
        start_time = time()
        for customer in self.customers:
            customer.simulate_period(date_from, date_to)
        end_time = time()
        print('Customers simulation done in %f seconds' % (end_time-start_time))

    def generate_test_load(self, date_from, date_to):
        if not self.customer_clusters:
            print('Analyze data first')
        else:
            self.load_simulator.copy_activity(self.customer_clusters, date_from, date_to)

    def generate_static_data(self):
        gen = MobileOperatorGenerator(verbose=True)
        gen.generate_static_data(self.main_session)

    def clear_main_base_data(self):
        self.metadata.drop_all(self.main_engine)
        self.generate_schema(self.main_engine)
        self.customer_clusters = {}

    def clear_test_base_data(self):
        self.metadata.drop_all(self.test_engine)
        self.generate_schema(self.test_engine)

    def analyze_data(self, date_from, date_to):
        self.customer_clusters = self.analyzer.analyze(date_from, date_to)


class MobileOperatorSystem:
    def __init__(self, session):
        self.session = session
        self.initial_balance = 200.0
        self.next_free_number = 0

    def get_active_balance_for_device(self, device):
        return device.account.balances[-1]
        # # TODO: Simplify (latest balance?)
        # # TODO: Also check due date
        # balance = self.session.query(Balance).\
        #     join(Account, Account.id == Balance.account_id).\
        #     join(CalculationMethod, Account.calculation_method_id == CalculationMethod.id).\
        #     join(Device, Device.account_id == Account.id).\
        #     filter(and_(Balance.account_id == device.account_id,
        #                 Balance.type == CalculationMethod.type,
        #                 Balance.due_date.is_(None))).one()
        # return balance

    def get_active_balance_for_account(self, account):
        return account.balances[-1]
        # # TODO: Simplify (latest balance?)
        # # TODO: Also check due date
        # balance = self.session.query(Balance).\
        #     join(Account, Account.id == Balance.account_id).\
        #     join(CalculationMethod, Account.calculation_method_id == CalculationMethod.id).\
        #     filter(and_(Balance.account_id == account.id,
        #                 Balance.type == CalculationMethod.type,
        #                 Balance.due_date.is_(None))).one()
        # return balance

    def get_unpaid_bills(self, account):
        # TODO: Handle date
        return self.session.query(Bill).\
            join(ServiceLog, Bill.service_log_id == ServiceLog.id).\
            join(DeviceService, ServiceLog.device_service_id == DeviceService.id).\
            join(Device, DeviceService.device_id == Device.id).\
            join(Account, and_(Device.account_id == Account.id,
                               Account.id == account.id)).\
            filter(Bill.debt > 0).all()

    def handle_request(self, request):
        logging.info('Handling request')

        request_date = request.date_from

        if request.type == 'activation':
            if request.service:
                return self.connect_service(request.device, request.service, connection_date=request_date)
            elif request.tariff:
                return self.connect_tariff(request.device, request.tariff, connection_date=request_date)
        elif request.type == 'deactivation':
            raise NotImplementedError
        elif request.type == 'status':
            logging.info('Doing nothing')
            return ServiceStatus.success

    def handle_payment(self, account, payment):
        logging.info('Handling payment')

        balance = self.get_active_balance_for_account(account)
        payment.balance = balance

        balance.amount += Decimal(payment.amount)
        logging.info('Replenishing %s balance at %f RUB' % (balance.type, payment.amount))
        # TODO: Implement bonuses charging
        if balance.type == 'credit':
            available_money = payment.amount
            # Paying unpaid bills
            unpaid_bills = self.get_unpaid_bills(account)
            for bill in unpaid_bills:
                bill_pay_sum = min(available_money, bill.debt)
                bill.paid += bill_pay_sum
                bill.debt -= bill_pay_sum
                available_money -= bill_pay_sum

        logging.info('New balance: %f RUB' % balance.amount)

    def handle_connected_service(self, service_info, free_activation=False):
        logging.info('Handling connected service')
        # TODO: Pass date through parameter
        connection_date = service_info.date_from
        log = ServiceLog(device_service=service_info,
                         use_date=connection_date,
                         action_type='activation',
                         amount=1)

        service = service_info.service
        self.session.add(log)

        if free_activation or service.activation_cost == Decimal(0):
            # logging.info('Activation is free')
            pass
        else:
            # TODO: Charge activation sum if latest tariff change was less than month ago
            # TODO: Handle charging subscription cost for current period
            logging.info('Writing bill: need to pay %f' % service.activation_cost)
            bill = Bill(date_from=connection_date, service_log=log, debt=service.activation_cost)
            log.bill = bill
            self.handle_bill(bill)

    def can_activate_service(self, device, service):
        balance = self.get_active_balance_for_device(device)

        if balance.type == 'advance':
            if balance.amount >= service.activation_cost:
                return True
            else:
                return False
        else:  # credit
            if balance.amount - service.activation_cost >= -balance.account.credit_limit:
                return True
            else:
                return False

    def get_device_location(self, device, date):
        return self.session.query(Location).filter(and_(Location.device == device,
                                                        Location.date_from <= date,
                                                        or_(Location.date_to.is_(None),
                                                            Location.date_to >= date))).one()

    def get_device_packet_services(self, device, service_name):
        return self.session.query(DeviceService).\
            join(Service, and_(DeviceService.service_id == Service.id,
                               DeviceService.device_id == device.id)).\
            join(Packet, and_(Packet.service_id == Service.id,
                              Packet.type == service_name)).\
            filter(DeviceService.is_activated).all()

    def get_regional_operator(self, operator_info):
        country = self.session.query(Country).filter_by(name=operator_info['country']).one()
        if 'region' in operator_info and operator_info['region'] is not None:
            region = self.session.query(Region).filter_by(country=country, name=operator_info['region']).one()
        else:
            region = None
        operator = self.session.query(MobileOperator).filter_by(name=operator_info['name'],
                                                                country=country, region=region).one()
        return operator

    def get_phone_number(self, operator_info, phone_info):
        phone_numbers = self.session.query(PhoneNumber).filter_by(area_code=phone_info['code'],
                                                                  number=phone_info['number']).all()  # FIXME: One
        if not phone_numbers:
            phone_number = self.register_phone_number(operator_info, phone_info)
        else:
            phone_number = phone_numbers[0]  # FIXME: Dirty hack
            logging.info('Phone number is already registered in base and belongs to operator %s %s' %
                         (phone_number.mobile_operator.name, phone_number.mobile_operator.country.iso3_code))
        return phone_number

    def register_phone_number(self, operator_info, phone_info):
        logging.info('Registering phone number %s of operator %s' % (phone_info, operator_info))

        regional_operator = self.get_regional_operator(operator_info)
        phone_number = PhoneNumber(area_code=phone_info['code'],
                                   number=phone_info['number'],
                                   mobile_operator=regional_operator)
        self.session.add(phone_number)
        self.session.flush([phone_number])

        return phone_number

    def round_call_duration(self, minutes, seconds):
        if minutes == 0:
            if seconds <= 3:
                return 0
            else:
                return 1
        else:
            if seconds == 0:
                return minutes
            else:
                return minutes+1

    def round_internet_session(self, megabytes, kilobytes):
        # FIXME: Correct rounding (up to 200 kilobytes)
        return megabytes

    def handle_bill(self, bill):
        device_service = bill.service_log.device_service
        service = device_service.service
        device = device_service.device
        logging.info('Handling bill for service %s. Need to pay: %f' % (service.name, bill.debt))
        balance = self.get_active_balance_for_device(device)

        if balance.type == 'advance':
            if balance.amount > 0:
                # Decreasing balance and paying bill
                logging.info('Debiting %s RUB from advance balance with %s RUS' % (bill.debt,
                                                                                   balance.amount))
                balance.amount -= bill.debt
                bill.paid = bill.debt
                bill.debt = 0
                return ServiceStatus.success
            else:
                return ServiceStatus.out_of_funds
        elif balance.type == 'credit':
            if balance.amount > -balance.account.credit_limit:
                # Decreasing balance, but the bill is still unpaid
                logging.info('Debiting %s RUB from credit balance with %s RUB' % (bill.debt,
                                                                                  balance.amount))
                # TODO: Write due date to bill
                balance.amount -= bill.debt
                return ServiceStatus.success
            else:
                return ServiceStatus.out_of_funds

    def handle_used_service(self, service_log):
        logging.info('Handling used service')

        service_info = service_log.device_service
        service = service_info.service
        device = service_info.device

        if service_log.is_free:
            return ServiceStatus.success

        unpaid_service_amount = service_log.amount

        packet_services = self.get_device_packet_services(device, service.name)
        if packet_services:
            # Placing packets in order: tariff packets, additional packets
            packet_charge_queue = deque()
            for packet_service in packet_services:
                if packet_service.packet_left > 0:
                    if packet_service in device.tariff.attached_services:
                        packet_charge_queue.appendleft(packet_service)
                    else:
                        packet_charge_queue.append(packet_service)

            if packet_charge_queue:
                logging.info('We can pay it from packets')
                # TODO: Handle packet restrictions

            # While we can pay service from packets
            while unpaid_service_amount > 0 and packet_charge_queue:
                packet_service_info = packet_charge_queue.pop()
                packet_charge = min(packet_service_info.packet_left, unpaid_service_amount)
                packet_service_info.packet_left -= packet_charge
                unpaid_service_amount -= packet_charge
                logging.info('Charging %d units from packet %s' % (packet_charge,
                                                                   packet_service_info.service.name))
                logging.info('Units left in packet: %d, unpaid units: %d' % (packet_service_info.packet_left,
                                                                             unpaid_service_amount))

                # TODO: Block services with packet_left == 0?

        if unpaid_service_amount > 0:
            if service.name == 'internet' and packet_services:
                # It is "unlimited", so additional charge is not required
                logging.info('Internet is now 64 kbit/sec')
            else:
                device_operator = device.phone_number.mobile_operator
                # TODO: Handle roaming
                if service_log.recipient_phone_number:
                    # It is outgoing call, sms, mms or internet
                    recipient_operator = service_log.recipient_phone_number.mobile_operator
                    try:
                        cost = self.session.query(Cost).filter(Cost.operator_from == device_operator,
                                                               Cost.operator_to == recipient_operator,
                                                               Cost.service == service).one()
                    except NoResultFound:
                        cost = self.session.query(Cost).filter(Cost.operator_from == device_operator,
                                                               Cost.service == service).one()
                else:
                    cost = self.session.query(Cost).filter(Cost.operator_from == device_operator,
                                                           Cost.service == service).one()

                logging.info('Writing bill: need to pay %f (%d * %f)' % (unpaid_service_amount*cost.use_cost,
                                                                         unpaid_service_amount,
                                                                         cost.use_cost))
                bill = Bill(service_log=service_log,
                            date_from=service_log.use_date,
                            debt=cost.use_cost*service_log.amount)
                service_log.bill = bill
                self.session.add(bill)
                return self.handle_bill(bill)
        else:
            return ServiceStatus.success

    def connect_tariff(self, device, tariff, free_activation=False, connection_date=db.func.now()):
        logging.info('Connecting tariff: %s' % tariff.name)

        if free_activation or self.can_activate_service(device, tariff):
            logging.info('Device can connect tariff')
        else:
            logging.info('The device has unpaid services. Connecting tariff is impossible')
            # TODO: Remove request? Request status?
            return ServiceStatus.out_of_funds

        # If device already has a tariff
        if device.tariff:
            if device.tariff.name == tariff.name:
                logging.info('The device has the same tariff')
                return ServiceStatus.fail
            else:
                logging.info("The device already has tariff '%s', disconnecting it first" % tariff.name)
                self.deactivate_service(device, tariff, connection_date, commit=False)
                for service in tariff.attached_services:
                    self.deactivate_service(device, service, connection_date, commit=False)

        device.tariff = tariff
        # Connecting tariff as a service
        self.connect_service(device, tariff, connection_date, free_activation=free_activation,
                             ability_check=False, flush=False)

        # Add to user basic services (like calls, sms, mms, internet)
        for service in tariff.attached_services:
            self.connect_service(device, service, connection_date, free_activation=free_activation,
                                 ability_check=False, flush=False)

        return ServiceStatus.success

    def connect_service(self, device, service, connection_date,
                        free_activation=False, ability_check=True, flush=True):
        logging.info('Connecting service: %s' % service.name)

        if ability_check:
            if free_activation or self.can_activate_service(device, service):
                logging.info('Device can connect service')
            else:
                logging.info('The device has unpaid services. Connecting service is impossible')
                return ServiceStatus.out_of_funds

        service_duration = service.duration_days
        if service_duration == 0:
            date_to = None
        else:
            date_to = connection_date + timedelta(days=service_duration)

        device_service = DeviceService(device=device, service=service, date_from=connection_date, date_to=date_to)
        logging.info('Connected service %s from %s to %s' % (service.name, connection_date, date_to))
        if service.packet:
            device_service.packet_left = service.packet.amount
        device.services.append(device_service)

        self.session.add(device_service)

        if flush:
            self.session.flush([device_service])

        self.handle_connected_service(device_service, free_activation=free_activation)

    def activate_service(self, device, service, date, flush=True):
        # TODO: Date?
        logging.info('Activating service: %s' % service.name)
        self.session.query(DeviceService).\
            filter_by(device=device, service=service, is_activated=False).\
            update({'is_activated': True},
                   synchronize_session='fetch')
        if flush:
            self.session.flush()

    def deactivate_service(self, device, service, date, flush=True):
        # TODO: Date?
        logging.info('Deactivating service: %s' % service.name)
        self.session.query(DeviceService).\
            filter_by(device=device, service=service, is_activated=True).\
            update({'is_activated': False,
                    'date_to': date},
                   synchronize_session='fetch')
        if flush:
            self.session.flush()

    def block_service(self, device, service, date, flush=True):
        # TODO: Date?
        logging.info('Blocking service: %s' % service.name)
        self.session.query(DeviceService).\
            filter_by(device=device, service=service, is_blocked=False).\
            update({'is_blocked': True},
                   synchronize_session='fetch')
        if flush:
            self.session.flush()

    def unlock_service(self, device, service, date, flush=True):
        # TODO: Date?
        logging.info('Blocking service: %s' % service.name)
        self.session.query(DeviceService).\
            filter_by(device=device, service=service, is_blocked=True).\
            update({'is_blocked': False},
                   synchronize_session='fetch')
        if flush:
            self.session.flush()

    def get_service(self, service_type='service', operator=None, name=None, code=None):
        logging.info('Getting service (type: %s) %s (code %s)' % (service_type, name, code))
        if service_type == 'service':
            service_entity = Service
        else:
            service_entity = Tariff

        if name:
            try:
                service = self.session.query(service_entity).filter_by(name=name, in_archive=False,
                                                                       operator=operator).one()
            except NoResultFound:
                service = self.session.query(service_entity).filter_by(name=name, in_archive=False).one()
        else:  # activation code
            try:
                service = self.session.query(service_entity).filter_by(activation_code=code,
                                                                       in_archive=False,
                                                                       operator=operator).one()
            except NoResultFound:
                service = self.session.query(service_entity).filter_by(activation_code=code, in_archive=False).one()

        return service

    def get_tariff_period(self, device):
        # TODO: Use subquery
        tariff_name = self.session.query(Tariff.name).join(Device, and_(Device.tariff_id == Tariff.id,
                                                                        Device.id == device.id)).one().name

        # TODO: Check date (it should be usable within simulation date)
        tariff_device_service = self.session.query(DeviceService).\
            join(Service, and_(DeviceService.service_id == Service.id)).\
            filter(and_(Service.name == tariff_name,
                        DeviceService.device_id == device.id,
                        DeviceService.is_activated)).one()

        period_start = tariff_device_service.date_from.date()
        period_end = tariff_device_service.date_to.date()
        return period_start, period_end

    def get_free_phone_number(self):
        logging.info('Getting free phone number')
        self.next_free_number += 1
        return '916', str(self.next_free_number).zfill(7)


class SimulatedCustomer:
    def __init__(self, customer, agreement_cluster_names, session, operator_system, verbose=False):
        logging.info('Registering customer')

        self.session = session
        self.system = operator_system
        self.customer = customer
        self.agreement_cluster_names = agreement_cluster_names
        self.verbose = verbose

        self.accounts = []
        self.devices = []

        session.add(self.customer)

    def generate_hierarchy(self, generation_date):
        logging.info('Generating agreements')
        for agreement_cluster_name in self.agreement_cluster_names:
            agreement_cluster_info = agreements_info[agreement_cluster_name]
            agreement_info = {
                'date': generation_date,
                'income_rating': agreement_cluster_info['income_rating']
            }
            agreement = self.sign_agreement(agreement_info)
            account_cluster_names = agreement_cluster_info['accounts']
            logging.info('Generating accounts')
            for account_cluster_name in account_cluster_names:
                account_cluster_info = accounts_info[account_cluster_name]
                account_info = {
                    'date': generation_date,
                    'calc_method': account_cluster_info['calculation_method'],
                    'cluster_id': account_cluster_info['cluster_id'],
                    'trust_category': account_cluster_info['trust_category'],
                    'credit_limit': account_cluster_info['credit_limit']
                }
                account = self.register_account(agreement, account_info)

                sim_acc = SimulatedAccount(self, account, account_cluster_info, self.session, self.system)
                sim_acc.generate_devices(generation_date)
                self.accounts.append(sim_acc)

    def sign_agreement(self, agreement_info):
        logging.info('Signing agreement: %s' % agreement_info)
        sign_date = agreement_info['date']

        agreement = self.session.query(Agreement).filter_by(destination=self.customer.type).one()
        c_agreement = CustomerAgreement(date_from=sign_date,
                                        signed_agreement=agreement)
        self.customer.agreements.append(c_agreement)
        return c_agreement

    def register_account(self, agreement, account_info):
        logging.info('Registering account: %s' % account_info)
        registration_date = account_info['date']

        calc_method = self.session.query(CalculationMethod).\
            filter_by(type=account_info['calc_method']).one()

        balance = Balance(date_from=registration_date,
                          type=calc_method.type,
                          amount=self.system.initial_balance)

        account = Account(date_from=registration_date,
                          cluster_id=account_info['cluster_id'],
                          calc_method=calc_method,
                          trust_category=account_info['trust_category'],
                          credit_limit=account_info['credit_limit'],
                          balances=[balance])

        agreement.accounts.append(account)
        return account

    def simulate_period(self, date_from, date_to):
        for account in self.accounts:
            account.simulate_period(date_from, date_to)
        self.session.commit()


class SimulatedAccount:
    def __init__(self, customer, account, account_cluster_info, session, operator_system):
        self.session = session
        self.customer = customer
        self.account = account
        self.account_cluster_info = account_cluster_info
        self.system = operator_system

        self.devices = []

    def add_device(self, device_info):
        logging.info('Attaching device to account: %s' % device_info)
        registration_date = device_info['date']

        device = Device(account=self.account,
                        date_from=registration_date,
                        cluster_id=device_info['cluster_id'],
                        IMEI=device_info['IMEI'],
                        type=device_info['type'])

        operator_info = device_info['operator']

        if 'phone_number' in device_info:
            phone_number_info = device_info['phone_number']
        else:
            code, number = self.system.get_free_phone_number()
            phone_number_info = {
                'code': code,
                'number': number
            }

        # TODO: Handle date
        phone_number = self.system.register_phone_number(operator_info, phone_number_info)
        device.phone_number = phone_number

        home_operator = phone_number.mobile_operator

        initial_location = Location(country=home_operator.country, region=home_operator.region,
                                    date_from=registration_date)
        device.locations.append(initial_location)

        initial_tariff_name = device_info['initial_tariff']
        logging.info('Should connect tariff %s' % initial_tariff_name)

        initial_tariff_name = 'Smart mini'  # FIXME: Delete when other tariffs will be in system
        tariff = self.system.get_service(service_type='tariff', name=initial_tariff_name, operator=home_operator)
        self.system.connect_tariff(device, tariff, free_activation=True,
                                   connection_date=registration_date)

        for initial_service_name in device_info['initial_services']:
            service = self.system.get_service(service_type='service', name=initial_service_name, operator=home_operator)
            self.system.connect_service(device, service, free_activation=True,
                                        connection_date=registration_date, flush=False)

        self.session.add(device)
        return device

    def generate_devices(self, generation_date):
        probabilistic = self.account_cluster_info['probabilistic']

        # Generating country distributions
        home_locations_info = self.account_cluster_info['home_locations']
        countries_distribution = distribution_from_list(home_locations_info)
        regions_distribution = {}

        for country_info in home_locations_info:
            country_name = country_info['name']
            if 'regions' in country_info:
                regions_distribution[country_name] = distribution_from_list(country_info['regions'])

        # Getting home location
        home_country = countries_distribution.get_value(return_array=False)
        home_region = None
        if home_country in regions_distribution:
            home_region = regions_distribution[home_country].get_value(return_array=False)

        if not probabilistic:  # fixed device clusters
            device_cluster_names = self.account_cluster_info['devices']
            for device_cluster_name in device_cluster_names:
                device_cluster_info = devices_info[device_cluster_name]

                # Getting initial tariff name
                tariff_distribution = distribution_from_list(device_cluster_info['Initial tariffs'])
                initial_tariff_name = tariff_distribution.get_value(return_array=False)

                # Getting initial services amount and names
                initial_services_info = device_cluster_info['Initial services']['services']
                service_distribution = distribution_from_list(initial_services_info)
                avg_amount = device_cluster_info['Initial services']['amount']
                max_deviation = device_cluster_info['Initial services']['max_deviation']
                amount = random.randint(max(0, avg_amount-max_deviation), avg_amount+max_deviation)
                initial_services = set()
                for i in range(amount):
                    initial_services.add(service_distribution.get_value(return_array=False))

                device_info = {
                    'cluster_id': device_cluster_info['cluster_id'],
                    'date': generation_date,
                    'initial_tariff': initial_tariff_name,
                    'initial_services': list(initial_services),
                    'IMEI': random_IMEI(),
                    'type': device_cluster_info['type'],
                    'operator': {
                        'name': 'MTS',
                        'country': home_country,
                        'region': home_region
                    }
                }

                home_region = {'country': home_country, 'region': home_region}

                device = self.add_device(device_info)
                self.devices.append(SimulatedDevice(self, device, device_cluster_info, home_region,
                                                    self.account.trust_category, self.session, self.system))
        else:
            raise NotImplementedError('probabilistic device generation is not yet supported')

    def make_payment(self, payment_info):
        logging.info('Making payment: %s' % payment_info)
        if payment_info['method'] == 'third_party':
            name = payment_info['name']
            payment_method = self.session.query(ThirdPartyCollection).filter_by(name=name).one()
        elif payment_info['method'] == 'cash':
            payment_method = self.session.query(Cash).one()
        else:  # credit card
            # TODO: Implement credit card payment
            raise NotImplementedError

        payment_date = payment_info['date']
        payment = Payment(date=payment_date, amount=payment_info['amount'], method=payment_method)

        self.session.add(payment)
        return self.system.handle_payment(self.account, payment)

    def simulate_period(self, date_from, date_to):
        gen = AccountActivityGenerator(self, date_from)  # TODO: When to start?
        account_actions = gen.generate_timeline(date_from, date_to)

        device_actions = []
        for device in self.devices:
            device_actions.extend(device.generate_period_actions(date_from, date_to))

        actions = account_actions+device_actions

        # TODO: Handle system changes every day
        for action in sorted(actions, key=lambda action: action.start_date):
            logging.info(action)
            action.perform()


class SimulatedDevice:
    def __init__(self, sim_account, device_entity, behavior_info, home_region, trust_category,
                 session, operator_system, verbose=False):
        self.session = session
        self.system = operator_system
        self.account = sim_account
        self.device = device_entity
        self.behavior_info = behavior_info
        self.home_region = home_region
        self.trust_category = trust_category
        self.verbose = verbose

    def set_device_location(self, location_info):
        country_name, region_name, place_name = None, None, None
        country_name = location_info['country']
        if 'region' in location_info:
            region_name = location_info['region']
        if 'place' in location_info:
            place_name = location_info['place']

        location_date = location_info['date']

        logging.info('Changing location to: Country = %s, Region = %s, Place = %s' % (country_name, region_name,
                                                                                      place_name))

        latest_location = self.session.query(Location).filter_by(device=self.device, date_to=None).one()
        latest_location.date_to = location_date

        region, place = None, None

        country = self.session.query(Country).filter_by(name=country_name).one()
        if region_name:
            region = self.session.query(Region).filter_by(country=country, name=region_name).one()
        if place_name:
            place = self.session.query(Place).filter_by(region=region, name=place_name).one()

        new_location = Location(device=self.device, date_from=location_date,
                                country=country, region=region, place=place)
        self.device.locations.append(new_location)
        self.session.flush([latest_location, new_location])

    def use_service(self, service_info, amount=1):
        recipient_phone_number = None
        usage_date = service_info['date']

        if 'phone_number' in service_info and 'operator' in service_info:
            operator_info = service_info['operator']
            phone_number_info = service_info['phone_number']
            recipient_phone_number = self.system.get_phone_number(operator_info, phone_number_info)

        device_service = self.session.query(DeviceService).\
            join(Service, and_(DeviceService.service_id == Service.id,
                               DeviceService.device_id == self.device.id,
                               DeviceService.is_activated,
                               Service.name == service_info['name'])).one()

        log = ServiceLog(device_service=device_service,
                         amount=amount,
                         action_type='usage',
                         use_date=usage_date,
                         is_free=service_info['is_free'],
                         recipient_phone_number=recipient_phone_number)

        self.session.add(log)
        return self.system.handle_used_service(log)

    def make_call(self, call_info):
        logging.info('Making call to phone number %s' % (call_info['phone_number']['code'] +
                                                         ' ' + call_info['phone_number']['number']))
        return self.use_service(call_info, self.system.round_call_duration(call_info['minutes'],
                                                                           call_info['seconds']))

    def send_message(self, message_info):
        phone_number = message_info['phone_number']['code'] + ' ' + message_info['phone_number']['number']
        logging.info('Sending %s message to phone number %s' % (message_info['name'], phone_number))
        return self.use_service(message_info, amount=1)

    def use_internet(self, session_info):
        logging.info('Using internet: %s' % session_info)
        return self.use_service(session_info, self.system.round_internet_session(session_info['megabytes'],
                                                                                 session_info['kilobytes']))

    def ussd_request(self, request_info):
        logging.info('Making request: %s' % request_info)

        regional_operator = self.device.phone_number.mobile_operator
        request_date = request_info['date']

        if request_info['service_type'] == 'service':
            service = self.system.get_service(service_type='service', operator=regional_operator,
                                              code=request_info['code'])
            request = Request(date_from=request_date, type=request_info['type'],
                              device=self.device, service=service)
        else:
            tariff = self.system.get_service(service_type='tariff', operator=regional_operator,
                                             code=request_info['code'])
            request = Request(date_from=request_date, type=request_info['type'],
                              device=self.device, tariff=tariff)
        self.session.add(request)
        return self.system.handle_request(request)

    def generate_period_actions(self, date_from, date_to):
        period_start, period_end = self.system.get_tariff_period(self.device)

        gen = DeviceActivityGenerator(self, period_start)
        actions = gen.generate_timeline(date_from, date_to)

        return actions
