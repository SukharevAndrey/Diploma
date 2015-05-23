from sqlalchemy import create_engine
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

        self.customers = []

    def generate_schema(self, engine):
        self.metadata.create_all(engine)

    def generate_customers(self):
        self.db1_engine.echo = True
        # for i in range(10):
        #     c = SimulatedCustomer(self.db1_session)
        #     self.customers.append(c)
        c = SimulatedCustomer(self.db1_session, verbose=True)
        aggr = c.sign_agreement()
        c.sign_agreement()
        c.sign_agreement()
        acc = c.register_account(aggr, 'advance')
        dev = c.add_device(acc)
        c.activate_tariff(dev, 'Smart mini')

    def initial_fill(self):
        gen = MobileOperatorGenerator(verbose=True)
        gen.generate_static_data(self.db1_session)
        # gen.generate_static_data(self.db2_session)

class SimulatedCustomer:
    def __init__(self, session, behavior_info=None, verbose=False):
        self.session = session
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
        device = random_device()
        device.account = account
        balance = Balance(amount=200)
        home_region = self.session.query(Region).filter_by(name='Moskva').one()
        home_operator = self.session.query(MobileOperator).filter_by(name='MTS', region=home_region).one()
        phone_number = PhoneNumber(area_code='916', number='1234567', mobile_operator=home_operator)
        device.balances.append(balance)
        device.phone_number = phone_number
        self.session.add(device)
        self.session.commit()
        return device

    def activate_tariff(self, device, tariff_name):
        regional_operator = device.phone_number.mobile_operator
        tariff = self.session.query(Tariff).filter_by(name=tariff_name,
                                                      operator=regional_operator).one()
        if device.tariff is not None:
            # TODO: Changing tariff. Beforehand we must delete all associated services and charge activation cost
            pass
            # for service in device.tariff.attached_services:
            #     self.session.delete(DeviceService).filter_by(device=device, service=service).one()

        for service in tariff.attached_services:
            device_service = DeviceService(service=service)
            if service.packet is not None:
                device_service.packet_left = service.packet.amount
            device.services.append(device_service)

        device.tariff = tariff
        device_tariff = DeviceService(service=tariff)
        device.services.append(device_tariff)

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

    def make_payment(self):
        pass

    def begin_simulation(self):
        pass

    def simulate_day(self):
        pass


def main():
    sim = MobileOperatorSimulator(base_schema)
    sim.initial_fill()
    sim.generate_customers()

if __name__ == '__main__':
    main()
