from datetime import datetime

from sqlalchemy import and_, inspect
from entities.customer import *
from entities.payment import *
from entities.service import *
from entities.location import *
from entities.operator import *

import logging

logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d.%m.%Y %H:%M:%S',
#                    level=logging.INFO)
#                     level=logging.CRITICAL)
                    filename='activity.log', filemode='w', level=logging.INFO)
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

class LoadSimulator:
    def __init__(self, main_session, test_session):
        self.main_session = main_session
        self.test_session = test_session

    def copy_static_data(self):
        print('Copying static data')
        agreements = self.main_session.query(Agreement).all()
        terms = self.main_session.query(TermOrCondition).all()
        payment_methods = self.main_session.query(PaymentMethod).all()
        calc_methods = self.main_session.query(CalculationMethod).all()
        countries = self.main_session.query(Country).all()
        regions = self.main_session.query(Region).all()
        operators = self.main_session.query(MobileOperator).all()
        phone_numbers = self.main_session.query(PhoneNumber).all()
        services = self.main_session.query(Service).all()
        costs = self.main_session.query(Cost).all()

        ins = inspect(agreements[0])
        print('Transient: {0}; Pending: {1}; Persistent: {2}; Detached: {3}'.format(ins.transient, ins.pending,
                                                                                    ins.persistent, ins.detached))

        self.main_session.expunge_all()

        ins = inspect(agreements[0])
        print('Transient: {0}; Pending: {1}; Persistent: {2}; Detached: {3}'.format(ins.transient, ins.pending,
                                                                                    ins.persistent, ins.detached))
        self.test_session.add_all(agreements)
        self.test_session.add_all(terms)
        self.test_session.add_all(payment_methods)
        self.test_session.add_all(calc_methods)
        self.test_session.add_all(countries)
        self.test_session.add_all(regions)
        self.test_session.add_all(operators)
        self.test_session.add_all(phone_numbers)
        self.test_session.add_all(services)
        self.test_session.add_all(costs)
        self.test_session.flush()
        print('Transient: {0}; Pending: {1}; Persistent: {2}; Detached: {3}'.format(ins.transient, ins.pending,
                                                                                    ins.persistent, ins.detached))
        self.test_session.commit()
        ins = inspect(agreements[0])
        print('Transient: {0}; Pending: {1}; Persistent: {2}; Detached: {3}'.format(ins.transient, ins.pending,
                                                                                    ins.persistent, ins.detached))

    def copy_preperiod_customers_data(self, customer_ids, period_start):
        print('Copying customers')
        period_start_date = datetime(period_start.year, period_start.month, period_start.day, 0, 0, 0)
        customers = self.main_session.query(Customer).\
            filter(and_(Customer.id.in_(customer_ids),
                        Customer.date_from < period_start_date)).all()

        agreements = self.main_session.query(CustomerAgreement).\
            filter(and_(CustomerAgreement.customer_id.in_(customer_ids),
                        CustomerAgreement.date_from < period_start_date)).all()
        agreement_ids = [agreement.id for agreement in agreements]

        accounts = self.main_session.query(Account).\
            filter(and_(Account.agreement_id.in_(agreement_ids),
                        Account.date_from < period_start_date)).all()
        account_ids = [account.id for account in accounts]

        balances = self.main_session.query(Balance).\
            filter(and_(Balance.account_id.in_(account_ids),
                        Balance.date_from < period_start_date)).all()

        devices = self.main_session.query(Device).\
            filter(and_(Device.account_id.in_(account_ids),
                        Device.date_from < period_start_date)).all()
        device_ids = [device.id for device in devices]

        device_services = self.main_session.query(DeviceService).\
            filter(and_(DeviceService.device_id.in_(device_ids),
                        DeviceService.date_from < period_start_date)).all()

        # Detaching all objects from main session
        self.main_session.expunge_all()

        self.test_session.add_all(customers)
        self.test_session.add_all(agreements)
        self.test_session.add_all(accounts)
        self.test_session.add_all(balances)
        self.test_session.add_all(devices)
        self.test_session.add_all(device_services)

    def copy_activity(self, customer_ids, date_from, date_to):
        ids_to_copy = customer_ids[0] + customer_ids[1]  # TODO: Select randomly n% from each cluster

        self.copy_static_data()
        self.copy_preperiod_customers_data(ids_to_copy, date_from)
        self.test_session.commit()
        agreements = self.test_session.query(CustomerAgreement).all()
        print(len(agreements))
        countries = self.test_session.query(Country).all()
        print(len(countries))