from datetime import date, datetime, timedelta
import random
from itertools import chain
import numpy as np

from sqlalchemy import and_, between
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

    def detached_objects(self, objects, to_list=False):
        if to_list:
            return list(map(self.make_transient, objects))
        else:
            return map(self.make_transient, objects)

    def copy_static_data(self):
        print('Copying static data')
        agreements = self.detached_objects(self.main_session.query(Agreement).all())
        terms = self.detached_objects(self.main_session.query(TermOrCondition).all())
        payment_methods = self.detached_objects(self.main_session.query(PaymentMethod).all())
        calc_methods = self.detached_objects(self.main_session.query(CalculationMethod).all())
        countries = self.detached_objects(self.main_session.query(Country).all())
        regions = self.detached_objects(self.main_session.query(Region).all())
        operators = self.detached_objects(self.main_session.query(MobileOperator).all())
        phone_numbers = self.detached_objects(self.main_session.query(PhoneNumber).all())
        services = self.detached_objects(self.main_session.query(Service).all())
        costs = self.detached_objects(self.main_session.query(Cost).all())

        self.test_session.add_all(chain(agreements, terms, payment_methods, calc_methods,
                                        countries, regions, operators, phone_numbers, services, costs))

    def copy_preperiod_customers_data(self, customer_ids, period_start):
        print('Copying preperiod data')
        period_start_date = datetime(period_start.year, period_start.month, period_start.day, 0, 0, 0)
        customers = self.detached_objects(self.main_session.query(Customer).
                                          filter(and_(Customer.id.in_(customer_ids),
                                                      Customer.date_from < period_start_date)).all(), to_list=True)

        agreements = self.detached_objects(self.main_session.query(CustomerAgreement).
                                           filter(and_(CustomerAgreement.customer_id.in_(customer_ids),
                                                       CustomerAgreement.date_from < period_start_date)).all(),
                                           to_list=True)
        agreement_ids = [agreement.id for agreement in agreements]

        accounts = self.detached_objects(self.main_session.query(Account).
                                         filter(and_(Account.agreement_id.in_(agreement_ids),
                                                     Account.date_from < period_start_date)).all(), to_list=True)
        account_ids = [account.id for account in accounts]

        balances = self.detached_objects(self.main_session.query(Balance).
                                         filter(and_(Balance.account_id.in_(account_ids),
                                                     Balance.date_from < period_start_date)).all(), to_list=True)

        devices = self.detached_objects(self.main_session.query(Device).
                                        filter(and_(Device.account_id.in_(account_ids),
                                                    Device.date_from < period_start_date)).all(), to_list=True)
        device_ids = [device.id for device in devices]

        locations = self.detached_objects(self.main_session.query(Location)
                                          .join(Device, Device.id == Location.device_id)
                                          .filter(and_(Device.id.in_(device_ids),
                                                       Location.date_from < period_start_date)).all(), to_list=True)

        device_services = self.detached_objects(self.main_session.query(DeviceService).
                                                filter(and_(DeviceService.device_id.in_(device_ids),
                                                            DeviceService.date_from < period_start_date)).all(),
                                                to_list=True)

        requests = self.detached_objects(self.main_session.query(Request).
                                         filter(and_(Request.device_id.in_(device_ids),
                                                     Request.date_from < period_start_date)).all(), to_list=True)

        self.test_session.add_all(chain(customers, agreements, accounts, balances,
                                        devices, locations, device_services, requests))

    def copy_period_activity(self, customer_ids, date_from, date_to):
        start_date = datetime(date_from.year, date_from.month, date_from.day, 0, 0, 0)
        end_date = datetime(date_to.year, date_to.month, date_to.day, 0, 0, 0) + timedelta(days=1)

        window_hours = 4

        step = timedelta(hours=window_hours)
        window_begin = start_date
        window_end = window_begin + timedelta(hours=window_hours)

        devices = self.detached_objects(self.main_session.query(Device)
                                        .join(Account, Account.id == Device.id)
                                        .join(CustomerAgreement, CustomerAgreement.id == Account.agreement_id)
                                        .join(Customer, Customer.id == CustomerAgreement.customer_id)
                                        .filter(Customer.id.in_(customer_ids)).all(), to_list=True)
        device_ids = [device.id for device in devices]

        while window_end <= end_date:
            print('Copying activity from %s to %s' % (window_begin, window_end))

            logs = self.detached_objects(self.main_session.query(ServiceLog)
                                         .join(DeviceService, DeviceService.id == ServiceLog.device_service_id)
                                         .join(Device, Device.id == DeviceService.device_id)
                                         .filter(and_(between(ServiceLog.date_from,
                                                              window_begin, window_end),
                                                      Device.id.in_(device_ids))).all(), to_list=True)
            log_ids = [log.id for log in logs]
            bills = self.detached_objects(self.main_session.query(Bill)
                                          .filter(and_(between(Bill.date_from, window_begin, window_end),
                                                       Bill.service_log_id.in_(log_ids))).all(), to_list=True)
            locations = self.detached_objects(self.main_session.query(Location)
                                              .join(Device, Device.id == Location.device_id)
                                              .filter(and_(Device.id.in_(device_ids),
                                                           between(Location.date_from,
                                                                   window_begin, window_end))).all(), to_list=True)
            requests = self.detached_objects(self.main_session.query(Request)
                                             .join(Device, Device.id == Request.device_id)
                                             .filter(and_(Device.id.in_(device_ids),
                                                          between(Request.date_from,
                                                                  window_begin, window_end))).all(), to_list=True)
            device_services = self.detached_objects(self.main_session.query(DeviceService)
                                                    .join(Device, Device.id == DeviceService.device_id)
                                                    .filter(and_(Device.id.in_(device_ids),
                                                                 between(DeviceService.date_from,
                                                                         window_begin, window_end))).all(),
                                                    to_list=True)
            balances = self.detached_objects(self.main_session.query(Balance)
                                             .join(Account, Account.id == Balance.account_id)
                                             .join(Device, Device.account_id == Account.id)
                                             .filter(and_(Device.id.in_(device_ids),
                                                          between(DeviceService.date_from,
                                                                  window_begin, window_end))).all(), to_list=True)

            entities = list(chain(logs, bills, locations, requests, device_services, balances))

            # Shifting dates
            delta = date.today()-entities[0].date_from.date()
            for entity in entities:
                entity.date_from += delta
                if hasattr(entity, 'date_to'):
                    entity.date_to += delta

            # TODO: Add entities according their time
            self.test_session.add_all(entities)
            self.test_session.flush()

            window_begin += step
            window_end += step

    def select_subset_of_customers(self, customer_clusters, load_factor):
        customer_ids = []
        for cluster_num in customer_clusters:
            cluster_size = len(customer_clusters[cluster_num])
            smaller_size = int(cluster_size*load_factor)
            ids = np.random.choice(customer_clusters[cluster_num], size=smaller_size, replace=False).tolist()
            customer_ids.extend(ids)
        return customer_ids

    def copy_activity(self, customer_clusters, load_factor, date_from, date_to):
        customer_ids = self.select_subset_of_customers(customer_clusters, load_factor)

        self.copy_static_data()
        self.test_session.flush()
        self.copy_preperiod_customers_data(customer_ids, date_from)
        self.test_session.commit()
        self.copy_period_activity(customer_ids, date_from, date_to)
        self.test_session.commit()
