from datetime import datetime, timedelta

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
    def __init__(self, session):
        self.session = session

    def analyze(self, date):
        print('Analyzing data')
        vec = DictVectorizer()
        devices_info = self.get_devices_info(date, date+timedelta(days=1))
        print(devices_info)
        processed_devices = vec.fit_transform(devices_info).toarray()
        # print('Processed')
        # print(processed_devices)

        min_max_scaler = preprocessing.MinMaxScaler()
        processed_devices = min_max_scaler.fit_transform(processed_devices)
        # print('Scaled')
        # print(processed_devices)

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        pca = PCA(n_components=3)
        X = pca.fit_transform(processed_devices)
        print(pca.explained_variance_ratio_)
        # print('X')
        # print(X)
        # estimator = DBSCAN(eps=10)
        estimator = DBSCAN(eps=0.2)
        estimator.fit(processed_devices)
        labels = estimator.labels_
        ax.scatter(X[:, 0], X[:, 1], X[:, 2], c=labels.astype(np.float))
        plt.show()

    def get_devices_info(self, date_from, date_to):
        date_begin = datetime(date_from.year, date_from.month, date_from.day, 0, 0, 0)
        date_end = datetime(date_to.year, date_to.month, date_to.day, 0, 0, 0)
        devices = self.session.query(Device).all()

        devices_info = []

        for device in devices:
            device_info = {'type': device.type,
                           'tariff': device.tariff.name}

            # Getting device services, which could be used on given time period
            connected_services = self.session.query(DeviceService).\
                filter(and_(DeviceService.device_id == device.id,
                            or_(DeviceService.date_to.is_(None),
                                DeviceService.date_to >= date_begin))).all()

            for device_service in connected_services:
                service = device_service.service
                #print(service.name)
                try:
                    total_usage, usage_amount = self.session.query(db.func.count(ServiceLog.id),
                                                                       db.func.sum(ServiceLog.amount)).\
                        filter(and_(ServiceLog.device_service == device_service,
                                    ServiceLog.action_type == 'usage',
                                    between(ServiceLog.use_date, date_begin, date_end))).\
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
                #print(total_usage, usage_amount, avg_amount)

            #print(device_info)
            devices_info.append(device_info)

        return devices_info