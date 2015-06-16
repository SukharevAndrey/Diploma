from datetime import datetime

from sqlalchemy import and_, inspect
from sqlalchemy.orm.session import make_transient
from entities.customer import *
from entities.payment import *
from entities.service import *
from entities.location import *
from entities.operator import *

import logging

# logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d.%m.%Y %H:%M:%S',
#                     #                    level=logging.INFO)
#                     #                     level=logging.CRITICAL)
#                     filename='activity.log', filemode='w', level=logging.INFO)
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


class LoadSimulator:
    def __init__(self, main_session, test_session):
        self.main_session = main_session
        self.test_session = test_session

    def make_transient(self, obj):
        make_transient(obj)
        return obj

    def copy_static_data(self):
        print('Copying static data')
        agreements = map(self.make_transient, self.main_session.query(Agreement).all())
        terms = map(self.make_transient, self.main_session.query(TermOrCondition).all())
        payment_methods = map(self.make_transient, self.main_session.query(PaymentMethod).all())
        calc_methods = map(self.make_transient, self.main_session.query(CalculationMethod).all())
        countries = map(self.make_transient, self.main_session.query(Country).all())
        regions = map(self.make_transient, self.main_session.query(Region).all())
        operators = map(self.make_transient, self.main_session.query(MobileOperator).all())
        phone_numbers = map(self.make_transient, self.main_session.query(PhoneNumber).all())
        services = map(self.make_transient, self.main_session.query(Service).all())
        costs = map(self.make_transient, self.main_session.query(Cost).all())

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

    def copy_preperiod_customers_data(self, customer_ids, period_start):
        print('Copying customers')
        period_start_date = datetime(period_start.year, period_start.month, period_start.day, 0, 0, 0)
        customers = list(map(self.make_transient, self.main_session.query(Customer).
                        filter(and_(Customer.id.in_(customer_ids),
                                    Customer.date_from < period_start_date)).all()))

        agreements = list(map(self.make_transient, self.main_session.query(CustomerAgreement).
                         filter(and_(CustomerAgreement.customer_id.in_(customer_ids),
                                     CustomerAgreement.date_from < period_start_date)).all()))
        agreement_ids = [agreement.id for agreement in agreements]

        accounts = list(map(self.make_transient, self.main_session.query(Account).
                       filter(and_(Account.agreement_id.in_(agreement_ids),
                                   Account.date_from < period_start_date)).all()))
        account_ids = [account.id for account in accounts]

        balances = list(map(self.make_transient, self.main_session.query(Balance).
                       filter(and_(Balance.account_id.in_(account_ids),
                                   Balance.date_from < period_start_date)).all()))

        devices = list(map(self.make_transient, self.main_session.query(Device).
                      filter(and_(Device.account_id.in_(account_ids),
                                  Device.date_from < period_start_date)).all()))
        device_ids = [device.id for device in devices]

        device_services = list(map(self.make_transient, self.main_session.query(DeviceService).
                              filter(and_(DeviceService.device_id.in_(device_ids),
                                          DeviceService.date_from < period_start_date)).all()))

        requests = list(map(self.make_transient, self.main_session.query(Request).
                       filter(and_(Request.device_id.in_(device_ids),
                                   Request.date_from < period_start_date)).all()))

        self.test_session.add_all(customers)
        self.test_session.add_all(agreements)
        self.test_session.add_all(accounts)
        self.test_session.add_all(balances)
        self.test_session.add_all(devices)
        self.test_session.add_all(device_services)
        self.test_session.add_all(requests)

    def copy_activity(self, customer_ids, date_from, date_to):
        ids_to_copy = customer_ids[0]+customer_ids[1]  # TODO: Select randomly n% from each cluster
        print(ids_to_copy)

        self.copy_static_data()
        self.test_session.flush()
        self.copy_preperiod_customers_data(ids_to_copy, date_from)
        self.test_session.commit()

        countries = self.test_session.query(Country).all()
        print(len(countries))
        customers = self.test_session.query(Customer).all()
        print(len(customers))
        c_agreements = self.test_session.query(CustomerAgreement).all()
        print(len(c_agreements))
