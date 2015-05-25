from decimal import Decimal

from sqlalchemy import create_engine, and_
from sqlalchemy.event import listens_for
from sqlalchemy.orm import scoped_session, sessionmaker

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

class MobileOperatorSimulator:
    def __init__(self, metadata):
        self.metadata = metadata
        self.db1_engine = create_engine('sqlite:///:memory:', pool_size=POOL_SIZE, echo=False)
        self.db2_engine = create_engine('sqlite:///:memory:', pool_size=POOL_SIZE, echo=False)

        self.generate_schema(self.db1_engine)
        self.generate_schema(self.db2_engine)

        self.db1_session = scoped_session(sessionmaker(bind=self.db1_engine))
        self.db2_session = scoped_session(sessionmaker(bind=self.db2_engine))

        self.initial_balance = 200

        self.system = MobileOperatorSystem(self.db1_session)

        self.customers = []

    def generate_schema(self, engine):
        self.metadata.create_all(engine)

    def generate_customers(self):
        #self.db1_engine.echo = True
        # for i in range(10):
        #     c = SimulatedCustomer(self.db1_session)
        #     self.customers.append(c)
        c = SimulatedCustomer(self.db1_session, self.system, verbose=True)
        c.begin_simulation()

    def initial_fill(self):
        gen = MobileOperatorGenerator(verbose=True)
        gen.generate_static_data(self.db1_session)
        # gen.generate_static_data(self.db2_session)


class MobileOperatorSystem:
    def __init__(self, session):
        self.session = session
        self.used_phone_numbers = set()

    def handle_request(self, request):
        print('Received request')
        if request.type == 'activation':
            if request.service is not None:
                self.connect_service(request.device, request.service)
            elif request.tariff is not None:
                self.connect_tariff(request.device, request.tariff)
        elif request.type == 'deactivation':
            raise NotImplementedError
        elif request.type == 'status':
            print('Doing nothing')

    def handle_payment(self, device, payment):
        print('Received payment')
        calc_method = device.account.calc_method

        if calc_method.type == 'advance':
            balance = self.session.query(Balance).filter_by(type='main', device=device).one()
        else:  # credit
            balance = self.session.query(Balance).filter_by(type='credit', device=device).one()

        payment.balance = balance
        balance.amount += payment.amount

        # TODO: Implement bonuses charging

        self.session.commit()

    def connect_tariff(self, device, tariff):
        print('Connecting tariff: ', tariff.name)
        # If device already has a tariff
        if device.tariff is not None:
            raise NotImplementedError

        # Add to user basic services (like calls, sms, mms, internet)
        for service in tariff.attached_services:
            self.connect_service(device, service, commit=False)

        device.tariff = tariff
        device_tariff = DeviceService(service=tariff)  # tariff as a service
        device.services.append(device_tariff)

        self.session.commit()

    def connect_service(self, device, service, commit=True):
        print('Connecting service: ', service.name)

        device_service = DeviceService(service=service)
        if service.packet is not None:
            device_service.packet_left = service.packet.amount
        device.services.append(device_service)

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

    def add_device(self, account):
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

    # def activate_tariff(self, device, info):
    #     regional_operator = device.phone_number.mobile_operator
    #     tariff_name = info['name']
    #     tariff = self.session.query(Tariff).filter_by(name=tariff_name,
    #                                                   operator=regional_operator,
    #                                                   in_archive=False).one()
    #     if device.tariff is not None:
    #         # Sending request
    #         request = Request(type='activation', device=device, service=tariff)
    #         self.session.add(request)
    #
    #         for service in device.tariff.attached_services:
    #             device_service = self.session.query(DeviceService).\
    #                 filter_by(device=device, service=service).one()
    #             device_service.is_activated = False
    #         cost_entity = tariff.costs[0]
    #         # TODO: Charge sum
    #
    #     for service in tariff.attached_services:
    #         device_service = DeviceService(service=service)
    #         if service.packet is not None:
    #             device_service.packet_left = service.packet.amount
    #         device.services.append(device_service)
    #
    #     device.tariff = tariff
    #     device_tariff = DeviceService(service=tariff)
    #     device.services.append(device_tariff)
    #
    #     self.session.commit()

    def block_service(self, device, service_name):
        regional_operator = device.phone_number.mobile_operator
        service = self.session.query(Service).\
            filter_by(name=service_name, operator=regional_operator).one()

        self.session.query(DeviceService).\
            filter(and_(DeviceService.is_activated,
                        DeviceService.service == service,
                        DeviceService.device == device)).\
            update({'is_blocked': True},
                   synchronize_session='fetch')

        self.session.commit()

    def activate_service(self, device, service_name):
        regional_operator = device.phone_number.mobile_operator
        service = self.session.query(Service).\
            filter_by(name=service_name, operator=regional_operator).one()

        self.session.query(DeviceService).\
            filter(and_(~DeviceService.is_activated,
                        DeviceService.service == service,
                        DeviceService.device == device)).\
            update({'is_activated': True},
                   synchronize_session='fetch')

        self.session.commit()

    def deactivate_service(self, device, service_name):
        regional_operator = device.phone_number.mobile_operator
        service = self.session.query(Service).\
            filter_by(name=service_name, operator=regional_operator).one()

        self.session.query(DeviceService).\
            filter(and_(DeviceService.is_activated,
                        DeviceService.service == service,
                        DeviceService.device == device)).\
            update({'is_activated': False},
                   synchronize_session='fetch')

        self.session.commit()

    # def connect_service(self, device, service_name):
    #     pass

    def make_call(self):
        pass

    def send_sms(self):
        pass

    def send_mms(self):
        pass

    def use_internet(self):
        pass

    def ussd_request(self, device, info):
        print('Making request: ', info)

        regional_operator = device.phone_number.mobile_operator

        if info['service_type'] == 'service':
            try:
                service = self.session.query(Service).\
                    filter_by(activation_code=info['code'], operator=regional_operator).one()
            except:
                service = self.session.query(Service).filter_by(activation_code=info['code']).one()
            request = Request(type=info['type'], device=device, service=service)
        else:
            try:
                tariff = self.session.query(Tariff).\
                    filter_by(activation_code=info['code'], operator=regional_operator).one()
            except:
                tariff = self.session.query(Tariff).filter_by(activation_code=info['code']).one()
            request = Request(type=info['type'], device=device, tariff=tariff)

        self.session.add(request)
        self.session.commit()
        self.system.handle_request(request)

    def make_payment(self, device, info):
        print('Making payment: ', info)
        if info['method'] == 'third_party':
            name = info['name']
            payment_method = self.session.query(ThirdPartyCollection).filter_by(name=name).one()
        elif info['method'] == 'cash':
            payment_method = self.session.query(Cash).one()
        else:  # credit card
            # TODO: Implement credit card payment
            raise NotImplementedError

        payment = Payment(amount=info['amount'], method=payment_method)
        # if self.customer_type == 'individual':
        #     balance = self.session.query(Balance).filter_by(type='main', device=device).one()
        # else:
        #     balance = self.session.query(Balance).filter_by(type='credit', device=device).one()
        # payment.balance = balance
        # balance.amount += Decimal(payment.amount)
        #
        #  (probably with events)

        self.session.add(payment)
        self.session.commit()
        self.system.handle_payment(device, payment)

    def begin_simulation(self):
        tariff_info = {
            'code': '*100*1#', # smart mini
            'type': 'activation',
            'service_type': 'tariff'
        }
        payment_info = {
            'amount': 100.0,
            'method': 'third_party',
            'name': 'QIWI'
        }
        balance_request_info = {
            'code': '*100#', # balance request
            'type': 'status',
            'service_type': 'service'
        }

        agreement = self.sign_agreement()
        self.sign_agreement()
        self.sign_agreement()
        account = self.register_account(agreement, 'advance')
        device = self.add_device(account)
        self.ussd_request(device, tariff_info)
        self.make_payment(device, payment_info)
        self.ussd_request(device, balance_request_info)

    def simulate_day(self):
        pass


def main():
    sim = MobileOperatorSimulator(base_schema)
    sim.initial_fill()
    sim.generate_customers()

if __name__ == '__main__':
    main()
