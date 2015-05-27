from decimal import Decimal
from datetime import datetime
from collections import deque

from sqlalchemy import create_engine, and_, or_
from sqlalchemy.sql import exists
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from base import Base
from generator import MobileOperatorGenerator
from random_data import *

from entities.customer import *
from entities.payment import *
from entities.service import *
from entities.operator import *
from entities.location import *

POOL_SIZE = 20
base_schema = Base.metadata

# TODO: Proper session handling
# TODO: Decimal service amount

class MobileOperatorSimulator:
    def __init__(self, metadata):
        self.metadata = metadata
        self.db1_engine = create_engine('sqlite:///:memory:', pool_size=POOL_SIZE, echo=False)
        # self.db2_engine = create_engine('sqlite:///:memory:', pool_size=POOL_SIZE, echo=False)

        self.generate_schema(self.db1_engine)
        # self.generate_schema(self.db2_engine)

        self.db1_session = scoped_session(sessionmaker(bind=self.db1_engine))
        # self.db2_session = scoped_session(sessionmaker(bind=self.db2_engine))

        self.system = MobileOperatorSystem(self.db1_session)

        self.customers = []

    def generate_schema(self, engine):
        self.metadata.create_all(engine)

    def generate_customers(self):
        self.db1_engine.echo = False
        c = SimulatedCustomer(self.db1_session, self.system, verbose=True)
        c.begin_simulation()

    def initial_fill(self):
        gen = MobileOperatorGenerator(verbose=True)
        gen.generate_static_data(self.db1_session)
        # gen.generate_static_data(self.db2_session)


class MobileOperatorSystem:
    def __init__(self, session):
        self.session = session
        self.initial_balance = 200.0

    def get_active_balance(self, device):
        calc_method = device.account.calc_method
        calc_to_type = {
            'advance': 'main',
            'credit': 'credit'
        }
        # TODO: Also check due date
        balance = self.session.query(Balance).\
            join(Device, Device.id == Balance.device_id).\
            filter(and_(Balance.type == calc_to_type[calc_method.type],
                        Balance.due_date.is_(None))).one()
        return balance

    def get_unpaid_bills(self, device):
        return self.session.query(Bill).\
            join(ServiceLog, Bill.service_log_id == ServiceLog.id).\
            join(DeviceService, ServiceLog.device_service_id == DeviceService.id).\
            join(Device, and_(DeviceService.device_id == Device.id,
                              Device.id == device.id)).\
            filter(Bill.debt > 0).all()

    def handle_request(self, request):
        print('Handling request')
        if request.type == 'activation':
            if request.service is not None:
                self.connect_service(request.device, request.service)
            elif request.tariff is not None:
                self.connect_tariff(request.device, request.tariff)
        elif request.type == 'deactivation':
            raise NotImplementedError
        elif request.type == 'status':
            print('Doing nothing')
            # TODO: Maybe send sms from system

    def handle_payment(self, device, payment):
        print('Handling payment')

        balance = self.get_active_balance(device)
        print('Replenishing %s balance at %f' % (balance.type, payment.amount))
        payment.balance = balance
        balance.amount += Decimal(payment.amount)
        print('Current balance: %f' % balance.amount)

        # TODO: Implement bonuses charging
        # TODO: Pay unpaid bills

        self.session.commit()

    def handle_connected_service(self, service_info):
        print('Handling connected service')
        log = ServiceLog(device_service=service_info,
                         amount=0)

        service = service_info.service
        self.session.add(log)

        if service.activation_cost == Decimal(0):
            print('Activation is free')
        else:
            # TODO: Charge activation sum if latest tariff change was less than month ago
            # TODO: Handle charging subscription cost for current period
            print('Writing bill: need to pay %f' % service.activation_cost)
            bill = Bill(service_log=log, debt=service.activation_cost)
            log.bill = bill
            self.handle_bill(bill)

        self.session.commit()

    def can_into_service(self, device):
        # unpaid_bills = self.get_unpaid_bills(device)
        # return not unpaid_bills
        balance = self.get_active_balance(device)
        print('Current balance: ', balance.amount)

        if balance.amount > 0:
            return True
        else:
            return False

    def get_device_location(self, device, date):
        # TODO: Get rid of exception (using or_)
        try:
            return self.session.query(Location).filter(and_(Location.device == device,
                                                            Location.date_from <= date,
                                                            Location.date_to >= date)).one()
        except NoResultFound:
            return device.locations[-1]

    def get_device_packet_services(self, device, service_name):
        return self.session.query(DeviceService).\
            join(Service, and_(DeviceService.service_id == Service.id,
                               DeviceService.device_id == device.id)).\
            join(Packet, and_(Packet.service_id == Service.id,
                              Packet.type == service_name)).\
            filter(DeviceService.is_activated).all()

    def get_phone_number(self, phone_info):
        try:
            phone_number = self.session.query(PhoneNumber).filter_by(area_code=phone_info['code'],
                                                                     number=phone_info['number']).one()
            print('Phone number is already registered in base and belongs to operator %s %s' %
                  (phone_number.mobile_operator.name, phone_number.mobile_operator.country.iso3_code))
        except NoResultFound:
            print('Phone number is not registered in base')
            phone_number = self.register_phone_number(phone_info, commit=False)
        return phone_number

    def register_phone_number(self, phone_info, commit=True):
        print('Registering phone number')
        operator_info = phone_info['operator']
        country = self.session.query(Country).filter_by(name=operator_info['country']).one()
        region = self.session.query(Region).filter_by(name=operator_info['region'],
                                                      country=country).one()
        regional_operator = self.session.query(MobileOperator).filter_by(name=operator_info['name'],
                                                                         country=country,
                                                                         region=region).one()
        phone_number = PhoneNumber(area_code=phone_info['code'],
                                   number=phone_info['number'],
                                   mobile_operator=regional_operator)
        self.session.add(phone_number)

        if commit:
            self.session.commit()

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
        print('Handling bill for service %s. Need to pay: %s' % (service.name, bill.debt))
        balance = self.get_active_balance(device)
        print('Debiting %s RUB from %s balance with balance %s. New balance: %s' % (bill.debt, balance.type,
                                                                                    balance.amount,
                                                                                    balance.amount-bill.debt))
        balance.amount -= bill.debt
        bill.debt = 0
        self.session.commit()

    def handle_used_service(self, service_log):
        print('Handling used service')

        service_info = service_log.device_service
        service = service_info.service
        device = service_info.device

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
                print('We can pay it from packets')
                # TODO: Handle packet restrictions

            # While we can pay service from packets
            while unpaid_service_amount > 0 and packet_charge_queue:
                packet_service_info = packet_charge_queue.pop()
                packet_charge = min(packet_service_info.packet_left, unpaid_service_amount)
                packet_service_info.packet_left -= packet_charge
                unpaid_service_amount -= packet_charge
                print('Charging %d units from packet %s' % (packet_charge,
                                                            packet_service_info.service.name))
                print('Units left in packet: %d, unpaid units: %d' % (packet_service_info.packet_left,
                                                                      unpaid_service_amount))

            # TODO: Block services with packet_left == 0?

        if unpaid_service_amount > 0:
            if service.name == 'internet' and packet_services:
                # It is "unlimited", so additional charge is not required
                print('Internet is now 64 kbit/sec')
            else:
                device_operator = device.phone_number.mobile_operator
                if service_log.recipient_phone_number:
                    # It is outgoing call, sms, mms or internet
                    recipient_operator = service_log.recipient_phone_number.mobile_operator
                    cost = self.session.query(Cost).filter(Cost.operator_from == device_operator,
                                                           Cost.operator_to == recipient_operator,
                                                           Cost.service == service).one()
                else:
                    cost = self.session.query(Cost).filter(Cost.operator_from == device_operator,
                                                           Cost.service == service).one()

                print('Writing bill: need to pay %f (%d * %f)' % (unpaid_service_amount*cost.use_cost,
                                                                  unpaid_service_amount,
                                                                  cost.use_cost))
                bill = Bill(debt=cost.use_cost*service_log.amount)
                service_log.bill = bill
                self.session.add(bill)
                self.session.commit()
                self.handle_bill(bill)

    def connect_tariff(self, device, tariff):
        print('Connecting tariff: ', tariff.name)

        if self.can_into_service(device):
            print('Device can connect tariff')
        else:
            print('The device has unpaid services. Connecting tariff is impossible')
            return

        # If device already has a tariff
        if device.tariff:
            print("The device already has tariff '%s', disconnecting it first" % tariff.name)
            for service in tariff.attached_services:
                self.deactivate_service(device, service, commit=False)

        device.tariff = tariff
        self.connect_service(device, tariff, ability_check=False, commit=False)  # connect tariff as a service

        # Add to user basic services (like calls, sms, mms, internet)
        for service in tariff.attached_services:
            self.connect_service(device, service, ability_check=False, commit=False)

        self.session.commit()

    def connect_service(self, device, service, ability_check=True, commit=True):
        print('Connecting service: ', service.name)

        if ability_check:
            if self.can_into_service(device):
                print('Device can connect service')
            else:
                print('The device has unpaid services. Connecting service is impossible')
                return

        device_service = DeviceService(device=device, service=service)
        if service.packet:
            device_service.packet_left = service.packet.amount
        device.services.append(device_service)

        self.session.add(device_service)

        if commit:
            self.session.commit()

        self.handle_connected_service(device_service)

    def activate_service(self, device, service, commit=True):
        print('Activating service: ', service.name)
        self.session.query(DeviceService).\
            filter_by(device=device, service=service, is_activated=False).\
            update({'is_activated': True},
                   synchronize_session='fetch')

        if commit:
            self.session.commit()

    def deactivate_service(self, device, service, commit=True):
        print('Deactivating service: ', service.name)
        self.session.query(DeviceService).\
            filter_by(device=device, service=service, is_activated=True).\
            update({'is_activated': False},
                   synchronize_session='fetch')
        if commit:
            self.session.commit()

    def block_service(self, device, service, commit=True):
        print('Blocking service: ', service.name)
        self.session.query(DeviceService).\
            filter_by(device=device, service=service, is_blocked=False).\
            update({'is_blocked': True},
                   synchronize_session='fetch')
        if commit:
            self.session.commit()

    def unlock_service(self, device, service, commit=True):
        print('Blocking service: ', service.name)
        self.session.query(DeviceService).\
            filter_by(device=device, service=service, is_blocked=True).\
            update({'is_blocked': False},
                   synchronize_session='fetch')
        if commit:
            self.session.commit()

    def get_free_phone_number(self):
        for area_code in ['916']:
            for number in range(9999999):
                print('yielding', area_code, str(number).zfill(7))
                yield area_code, str(number).zfill(7)


class SimulatedCustomer:
    def __init__(self, session, operator_system, behavior_info=None, verbose=False):
        self.session = session
        self.system = operator_system
        self.customer = random_individual()
        self.customer_type = 'individual'
        self.verbose = verbose

        session.add(self.customer)
        session.commit()

    def sign_agreement(self):
        agreement = self.session.query(Agreement).filter_by(destination=self.customer_type).one()
        c_agreement = CustomerAgreement(signed_agreement=agreement)
        self.customer.agreements.append(c_agreement)
        self.session.commit()
        return c_agreement

    def register_account(self, agreement, calculation_method_type):
        calc_method = self.session.query(CalculationMethod).\
            filter_by(type=calculation_method_type).one()
        account = Account(calc_method=calc_method)
        agreement.accounts.append(account)
        self.session.commit()
        return account

    def add_device(self, account, device_info=None):
        print('Attaching device')
        device = random_device()
        device.account = account
        balance = Balance(amount=200)
        home_region = self.session.query(Region).filter_by(name='Moskva').one()
        home_operator = self.session.query(MobileOperator).filter_by(name='MTS', region=home_region).one()
        # area_code, number = self.system.get_free_phone_number()
        area_code, number = '916', '0000000'
        phone_number = PhoneNumber(area_code=area_code, number=number, mobile_operator=home_operator)
        device.balances.append(balance)
        device.phone_number = phone_number
        self.session.add(device)
        self.session.commit()
        return device

    def set_device_location(self, device, location_info):
        country_name, region_name, place_name = None, None, None
        country_name = location_info['country']
        if 'region' in location_info:
            region_name = location_info['region']
        if 'place' in location_info:
            place_name = location_info['place']

        if 'date' in location_info:
            location_date = location_info['date']
        else:
            location_date = db.func.now()

        print('Changing location to: Country = %s, Region = %s, Place = %s' % (country_name, region_name, place_name))
        if device.locations:
            latest_location = self.session.query(Location).filter_by(device=device, date_to=None).one()
            latest_location.date_to = location_date

        region, place = None, None

        country = self.session.query(Country).filter_by(name=country_name).one()
        if region_name:
            region = self.session.query(Region).filter_by(country=country, name=region_name).one()
        if place_name:
            place = self.session.query(Place).filter_by(region=region, name=place_name).one()

        new_location = Location(date_from=location_date, country=country, region=region, place=place)
        device.locations.append(new_location)

        self.session.commit()

    def use_service(self, device, service_info, amount=1):
        if self.system.can_into_service(device):
            print('Device can use service')
        else:
            print('The device has unpaid services. Using the service is impossible')
            return

        recipient_phone_number = None

        if 'recipient' in service_info:
            recipient_info = service_info['recipient']
            recipient_phone_number = self.system.get_phone_number(recipient_info)

        device_service = self.session.query(DeviceService).\
            join(Service, and_(DeviceService.service_id == Service.id,
                               DeviceService.device_id == device.id,
                               DeviceService.is_activated,
                               Service.name == service_info['name'])).one()

        log = ServiceLog(device_service=device_service,
                         amount=amount,
                         recipient_phone_number=recipient_phone_number)

        self.session.add(log)
        self.session.commit()
        self.system.handle_used_service(log)

    def make_call(self, device, call_info):
        print('Making call to phone number %s' % (call_info['recipient']['code'] +
                                                  ' ' + call_info['recipient']['number']))
        # TODO: Save original call duration
        self.use_service(device, call_info, self.system.round_call_duration(call_info['minutes'], call_info['seconds']))

    def send_sms(self, device, sms_info):
        print('Sending sms to phone number %s' % (sms_info['recipient']['code'] +
                                                  ' ' + sms_info['recipient']['number']))
        self.use_service(device, sms_info, 1)

    def send_mms(self, device, mms_info):
        print('Sending sms to phone number %s' % (mms_info['recipient']['code'] +
                                                  ' ' + mms_info['recipient']['number']))
        self.use_service(device, mms_info, 1)

    def use_internet(self, device, session_info):
        print('Using internet')
        self.use_service(device, session_info, self.system.round_internet_session(session_info['megabytes'],
                                                                                  session_info['kilobytes']))

    def ussd_request(self, device, request_info):
        print('Making request: ', request_info)

        regional_operator = device.phone_number.mobile_operator

        if request_info['service_type'] == 'service':
            try:
                service = self.session.query(Service).\
                    filter_by(activation_code=request_info['code'], operator=regional_operator).one()
            except NoResultFound:
                service = self.session.query(Service).filter_by(activation_code=request_info['code']).one()
            request = Request(type=request_info['type'], device=device, service=service)
        else:
            try:
                tariff = self.session.query(Tariff).\
                    filter_by(activation_code=request_info['code'], operator=regional_operator).one()
            except NoResultFound:
                tariff = self.session.query(Tariff).filter_by(activation_code=request_info['code']).one()
            request = Request(type=request_info['type'], device=device, tariff=tariff)

        self.session.add(request)
        self.session.commit()
        self.system.handle_request(request)

    def make_payment(self, device, payment_info):
        print('Making payment: ', payment_info)
        if payment_info['method'] == 'third_party':
            name = payment_info['name']
            payment_method = self.session.query(ThirdPartyCollection).filter_by(name=name).one()
        elif payment_info['method'] == 'cash':
            payment_method = self.session.query(Cash).one()
        else:  # credit card
            # TODO: Implement credit card payment
            raise NotImplementedError

        payment = Payment(amount=payment_info['amount'], method=payment_method)

        self.session.add(payment)
        self.session.commit()
        self.system.handle_payment(device, payment)

    def begin_simulation(self):
        tariff_info = {
            'code': '*100*1#',  # smart mini
            'type': 'activation',
            'service_type': 'tariff'
        }
        service_info = {
            'code': '*252#',  # BIT
            'type': 'activation',
            'service_type': 'service'
        }
        payment_info = {
            'amount': 100.0,
            'method': 'third_party',
            'name': 'QIWI'
        }
        balance_request_info = {
            'code': '*100#',  # balance request
            'type': 'status',
            'service_type': 'service'
        }
        sms_info = {
            'name': 'sms',
            'text': 'Lorem ipsum',
            'recipient': {
                'code': '916',
                'number': '1234567',
                'operator': {
                    'name': 'MTS',
                    'country': 'Russia',
                    'region': 'Moskva'
                }
            }
        }
        call_info = {
            'name': 'outgoing_call',
            'minutes': 5,
            'seconds': 12,
            'recipient': {
                'code': '916',
                'number': '7654321',
                'operator': {
                    'name': 'MTS',
                    'country': 'Russia',
                    'region': 'Moskva'
                }
            }
        }
        internet_session_info = {
            'name': 'internet',
            'megabytes': 50,
            'kilobytes': 21
        }
        location1_info = {
            'country': 'Russia',
            'region': 'Moskva',
            'date': datetime(2015, 5, 26, 0, 0, 0)
        }
        location2_info = {
            'country': 'Russia',
            'region': 'Brjanskaja',
            'date': datetime.now()
        }
        account_info = {

        }
        device_info = {

        }
        agreement = self.sign_agreement()
        self.sign_agreement()
        self.sign_agreement()
        account = self.register_account(agreement, 'advance')
        device = self.add_device(account)
        self.set_device_location(device, location1_info)
        self.ussd_request(device, tariff_info)  # connecting tariff
        # self.ussd_request(device, tariff_info)  # connecting it again
        self.ussd_request(device, service_info)  # connecting BIT
        self.make_payment(device, payment_info)
        self.ussd_request(device, balance_request_info)
        # for i in range(51):
        #     self.send_sms(device, sms_info)
        self.send_sms(device, sms_info)
        self.make_call(device, call_info)
        self.use_internet(device, internet_session_info)
        self.set_device_location(device, location2_info)
        self.ussd_request(device, tariff_info)  # connecting tariff again
        self.ussd_request(device, tariff_info)  # connecting tariff again
        bills = self.system.get_unpaid_bills(device)
        print(bills)
        # for location in device.locations:
        #     print(location.country.name, location.region.name, location.date_from, location.date_to)
        # #location = self.system.get_device_location(device, datetime(2015, 5, 26, 0, 0, 0))
        # location = self.system.get_device_location(device, datetime.now())
        # print(location.country.name, location.region.name)

    def simulate_day(self):
        pass


def main():
    sim = MobileOperatorSimulator(base_schema)
    sim.initial_fill()
    sim.generate_customers()

if __name__ == '__main__':
    main()
