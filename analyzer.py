from datetime import datetime, timedelta
from time import time

from sqlalchemy import and_, or_, between
from sqlalchemy.orm.exc import NoResultFound

from entities.customer import *
from entities.service import *

import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn import preprocessing
from sklearn.cluster import KMeans, DBSCAN, MiniBatchKMeans
from sklearn.decomposition import PCA
from sklearn import metrics
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt

class ActivityAnalyzer:
    def __init__(self, main_session, test_session):
        self.main_session = main_session
        self.test_session = test_session

    def get_devices_info(self, date_from, date_to):
        date_begin = datetime(date_from.year, date_from.month, date_from.day, 0, 0, 0)
        date_end = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59)

        devices = self.main_session.query(Device).order_by(Device.id).all()
        devices_info = []
        device_original_labels = []
        device_ids = []

        i = 0
        for device in devices:
            device_info = {'type': device.type,
                           'tariff': device.tariff.name}

            # Getting device services, which could be used on given time period
            # TODO: Date from?
            connected_services = self.main_session.query(DeviceService).\
                filter(and_(DeviceService.device_id == device.id,
                            or_(DeviceService.date_to.is_(None),
                                DeviceService.date_to >= date_begin))).all()

            for device_service in connected_services:
                service = device_service.service
                try:
                    total_usage, usage_amount = self.main_session.query(db.func.count(ServiceLog.id),
                                                                        db.func.sum(ServiceLog.amount)).\
                        filter(and_(ServiceLog.device_service == device_service,
                                    ServiceLog.action_type == 'usage',
                                    between(ServiceLog.date_from, date_begin, date_end))).\
                        group_by(ServiceLog.device_service_id).one()
                except NoResultFound:
                    total_usage = 0
                    usage_amount = 0

                if total_usage > 0:
                    avg_amount = usage_amount/total_usage
                else:
                    avg_amount = 0

                if service.name == 'outgoing_call':
                    device_info['calls'] = total_usage
                    device_info['avg_call_duration'] = avg_amount
                elif service.name == 'sms':
                    device_info['sms'] = total_usage
                elif service.name == 'mms':
                    device_info['mms'] = total_usage
                elif service.name == 'internet':
                    device_info['internet_usage'] = total_usage*usage_amount
                else:
                    if 'other_usages' not in device_info:
                        device_info['other_usages'] = total_usage
                    else:
                        device_info['other_usages'] += total_usage

            devices_info.append(device_info)
            device_ids.append(device.id)
            device_original_labels.append(device.cluster_id)
            i += 1

        return devices_info, device_original_labels, device_ids

    def get_clusters_mask(self, clusters, n):
        mask = np.zeros(n)
        for cluster in clusters:
            mask[cluster] += 1
        return mask

    def get_accounts_info(self, device_cluster_match, device_clusters_amount):
        accounts = self.main_session.query(Account).order_by(Account.id).all()
        account_infos = []
        account_original_labels = []
        account_ids = []
        device_masks = []

        for account in accounts:
            account_info = {
                'trust_category': account.trust_category,
                'credit_limit': float(account.credit_limit),
                'bill_group': account.bill_group,
                'calc_method_id': account.calculation_method_id
            }

            devices = self.main_session.query(Device).filter_by(account_id=account.id).all()
            account_info['devices_amount'] = len(devices)
            device_clusters = []
            for device in devices:
                device_clusters.append(device_cluster_match[device.id])
            device_cluster_mask = self.get_clusters_mask(device_clusters, device_clusters_amount)

            device_masks.append(device_cluster_mask)
            account_original_labels.append(account.cluster_id)
            account_infos.append(account_info)
            account_ids.append(account.id)

        return account_infos, account_original_labels, device_masks, account_ids

    def get_customers_info(self, account_cluster_match, account_clusters_amount):
        customers = self.main_session.query(Customer).order_by(Customer.id).all()
        customer_infos = []
        customer_original_labels = []
        customer_ids = []
        account_masks = []

        for customer in customers:
            customer_info = {
                'customer_type': customer.type,
                'status': customer.status,
                'rank': customer.rank,
            }
            # TODO: Individual and Organization features
            if customer.type == 'individual':
                pass
            else:
                pass

            agreements = self.main_session.query(CustomerAgreement).filter_by(customer_id=customer.id).all()
            customer_info['agreements_amount'] = len(agreements)

            accounts_cluster_mask = np.zeros(account_clusters_amount)
            # Accumulating information about all accounts
            for agreement in agreements:
                accounts = self.main_session.query(Account).filter_by(agreement_id=agreement.id).all()

                account_clusters = []
                for account in accounts:
                    account_clusters.append(account_cluster_match[account.id])
                account_cluster_mask = self.get_clusters_mask(account_clusters, account_clusters_amount)
                accounts_cluster_mask += account_cluster_mask

            account_masks.append(accounts_cluster_mask)
            customer_original_labels.append(customer.cluster_id)
            customer_infos.append(customer_info)
            customer_ids.append(customer.id)

        return customer_infos, customer_original_labels, account_masks, customer_ids

    def plot_data(self, data, labels):
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        pca = PCA(n_components=3)
        X = pca.fit_transform(data)
        print('Projected components:')
        print(pca.components_)
        print('Projected vectors variance:')
        print(pca.explained_variance_ratio_)

        ax.scatter(X[:, 0], X[:, 1], X[:, 2], c=labels.astype(np.float))
        plt.show()

    def print_metrics(self, data, labels, labels_real):
        print("Homogeneity: %0.3f" % metrics.homogeneity_score(labels_real, labels))
        print("Completeness: %0.3f" % metrics.completeness_score(labels_real, labels))
        print("V-measure: %0.3f" % metrics.v_measure_score(labels_real, labels))
        print("Adjusted Rand Index: %0.3f"
              % metrics.adjusted_rand_score(labels_real, labels))
        print("Adjusted Mutual Information: %0.3f"
              % metrics.adjusted_mutual_info_score(labels_real, labels))
        print("Silhouette Coefficient: %0.3f"
              % metrics.silhouette_score(data, labels))

    def analyze(self, date_from, date_to):
        print('Analyzing data')
        start_time = time()

        vectorizer = DictVectorizer()

        # Clustering devices
        devices_info, device_labels, device_ids = self.get_devices_info(date_from, date_to)
        processed_devices = vectorizer.fit_transform(devices_info).toarray()

        min_max_scaler = preprocessing.MinMaxScaler()
        processed_devices = min_max_scaler.fit_transform(processed_devices)

        # estimator = DBSCAN(eps=0.3)  # TODO: Scaling eps
        device_estimator = KMeans(n_clusters=2, n_jobs=-1)
        device_estimator.fit(processed_devices)
        estimated_device_labels = device_estimator.labels_

        labels_set = set(estimated_device_labels)
        print('Estimated number of device clusters: %d' % (len(labels_set)))
        print(labels_set)

        device_cluster_match = {}
        for i, device_id in enumerate(device_ids):
            device_cluster_match[device_id] = estimated_device_labels[i]

        accounts_info, account_labels, device_masks, account_ids = self.get_accounts_info(device_cluster_match, 2)
        processed_accounts = vectorizer.fit_transform(accounts_info).toarray()

        # Adding device clusters info to accounts
        processed_accounts = np.concatenate((processed_accounts, device_masks), axis=1)
        processed_accounts = min_max_scaler.fit_transform(processed_accounts)

        account_estimator = KMeans(n_clusters=2, n_jobs=-1)
        account_estimator.fit(processed_accounts)
        estimated_account_labels = account_estimator.labels_

        account_labels_set = set(estimated_device_labels)
        print('Estimated number of account clusters: %d' % (len(account_labels_set)))
        print(account_labels_set)

        account_cluster_match = {}
        for i, account_id in enumerate(account_ids):
            account_cluster_match[account_id] = estimated_account_labels[i]

        customers_info, customer_labels, account_masks, customer_ids = self.get_customers_info(account_cluster_match, 2)
        processed_customers = vectorizer.fit_transform(customers_info).toarray()

        # Adding account clusters info to customers
        processed_customers = np.concatenate((processed_customers, account_masks), axis=1)
        processed_customers = min_max_scaler.fit_transform(processed_customers)

        customer_estimator = KMeans(n_clusters=2, n_jobs=-1)
        customer_estimator.fit_transform(processed_customers)
        estimated_customer_labels = customer_estimator.labels_

        customer_labels_set = set(estimated_customer_labels)
        print('Estimated number of customer clusters: %d' % (len(customer_labels_set)))
        print(customer_labels_set)

        customer_clusters = {}
        for i, customer_id in enumerate(customer_ids):
            cluster = estimated_customer_labels[i]
            if cluster not in customer_clusters:
                customer_clusters[cluster] = [customer_id]
            else:
                customer_clusters[cluster].append(customer_id)
        print('Customer clusters')
        print(customer_clusters)

        end_time = time()
        print('Analyzing took %f seconds' % (end_time-start_time))

        self.print_metrics(processed_devices, estimated_device_labels, device_labels)
        self.plot_data(processed_devices, estimated_device_labels)

        self.print_metrics(processed_accounts, estimated_account_labels, account_labels)
        # self.plot_data(processed_accounts, estimated_account_labels)

        self.print_metrics(processed_customers, estimated_customer_labels, customer_labels)
        # self.plot_data(processed_customers, estimated_customer_labels)

        return customer_clusters

def main():
    pass

if __name__ == '__main__':
    main()
