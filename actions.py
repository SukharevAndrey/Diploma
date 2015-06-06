from abc import ABCMeta, abstractmethod
import random
from datetime import timedelta

class OverlapError(Exception):
    pass


class Action(metaclass=ABCMeta):
    def __init__(self, start_date):
        self.start_date = start_date

    @abstractmethod
    def to_dict_info(self):
        pass

    @abstractmethod
    def perform(self):
        pass


class CustomerAction(Action):
    def __init__(self, customer, start_date):
        super().__init__(start_date)
        self.customer = customer


class DeviceAction(Action):
    def __init__(self, device, start_date):
        super().__init__(start_date)
        self.device = device


class Call(DeviceAction):
    def __init__(self, device, start_date, maximum_duration, can_overlap=False):
        super().__init__(device, start_date)
        self._duration = None
        self.end_date = None
        self.maximum_duration = maximum_duration
        self.recipient_info = None
        self.can_overlap = can_overlap

    @property
    def duration(self):
        return self._duration

    @duration.setter
    def duration(self, duration):
        if self.can_overlap:
            self._duration = duration
        else:
            if not self.maximum_duration or duration < self.maximum_duration:
                self._duration = duration
                self.end_date = self.start_date+duration
            else:
                raise OverlapError('call intersects with next one')

    def generate_duration(self, distribution):
        for i in range(10):
            duration_minutes = int(distribution.get_value())
            duration_seconds = random.randint(0, 59)
            duration = timedelta(minutes=duration_minutes, seconds=duration_seconds)
            try:
                self.duration = duration
            except OverlapError:
                continue
            return
        # fail safe
        self.duration = timedelta(minutes=0, seconds=1)

    def get_call_duration(self):
        raw_seconds = self.duration.seconds
        return divmod(raw_seconds, 60)

    def to_dict_info(self):
        dur_minutes, dur_seconds = self.get_call_duration()
        call_info = {
            'date': self.start_date,
            'name': 'outgoing_call',
            'minutes': dur_minutes,
            'seconds': dur_seconds,
            'operator': {
                'name': 'MTS',
                'country': 'Russia',
                'region': 'Moskva'
            },
            'phone_number': {
                'code': '916',
                'number': '7654321',
            }
        }
        return call_info

    def perform(self):
        call_info = self.to_dict_info()
        self.device.make_call(call_info)

    def __repr__(self):
        return '%s - Outgoing call to %s, duration: %s' % (self.start_date.time(), self.recipient_info, self.duration)


class Internet(DeviceAction):
    def __init__(self, device, start_date):
        super().__init__(device, start_date)
        self.megabytes = 0
        self.kilobytes = 0

    def generate_service_usage(self, distribution):
        self.megabytes = int(distribution.get_value(return_array=False))
        self.kilobytes = random.randint(0, 1023)

    def to_dict_info(self):
        return {'date': self.start_date,
                'name': 'internet',
                'megabytes': self.megabytes,
                'kilobytes': self.kilobytes}

    def perform(self):
        session_info = self.to_dict_info()
        self.device.use_internet(session_info)

    def __repr__(self):
        return '%s - Internet usage. Used %s mb, %s kb' % (self.start_date.time(), self.megabytes, self.kilobytes)


class SMS(DeviceAction):
    def __init__(self, device, start_date, recipient_info=None):
        super().__init__(device, start_date)
        self.recipient = recipient_info

    def to_dict_info(self):
        sms_info = {
            'date': self.start_date,
            'name': 'sms',
            'text': 'Lorem ipsum',
            'operator': {
                'name': 'MTS',
                'country': 'Russia',
                'region': 'Moskva'
            },
            'phone_number': {
                'code': '916',
                'number': '1234567',
            }
        }
        return sms_info

    def perform(self):
        sms_info = self.to_dict_info()
        self.device.send_sms(sms_info)

    def __repr__(self):
        return '%s - SMS Message. Sent to %s' % (self.start_date.time(), self.recipient)


class OneTimeService(DeviceAction):
    def __init__(self, device, start_date, service_name, activation_code, type):
        super().__init__(device, start_date)
        self.activation_code = activation_code
        self.service_name = service_name
        self.type = type

    def to_dict_info(self):
        return {'date': self.start_date,
                'code': self.activation_code,
                'type': self.type,
                'service_type': 'service'}

    def perform(self):
        service_info = self.to_dict_info()
        self.device.ussd_request(service_info)

    def __repr__(self):
        return '%s - USSD request. Service: %s, code: %s' % (self.start_date.time(),
                                                             self.service_name, self.activation_code)


class MMS(DeviceAction):
    def __init__(self, device, start_date, recipient_info=None):
        super().__init__(device, start_date)
        self.recipient = recipient_info

    def to_dict_info(self):
        return {}

    def perform(self):
        pass

    def __repr__(self):
        return '%s - MMS Message. Sent to %s' % (self.start_date.time(), self.recipient)


class TariffChange(DeviceAction):
    def __init__(self, device, start_date, tariff_code, tariff_name):
        super().__init__(device, start_date)
        self.tariff_code = tariff_code
        self.tariff_name = tariff_name

    def to_dict_info(self):
        return {'date': self.start_date,
                'code': self.tariff_code,
                'type': 'activation',
                'service_type': 'tariff'}

    def perform(self):
        tariff_info = self.to_dict_info()
        self.device.ussd_request(tariff_info)

    def __repr__(self):
        return '%s - Changing tariff to %s' % (self.start_date.time(), self.tariff_name)