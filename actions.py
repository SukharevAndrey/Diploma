from abc import ABCMeta, abstractmethod
import random
from datetime import timedelta

from status import ServiceStatus


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

    def handle_out_of_funds(self):
        print('Handling out of funds situation')


class DevicePayment(DeviceAction):
    def __init__(self, device, start_date, method_name, method_type, payment_sum):
        super().__init__(device, start_date)
        self.method_name = method_name
        self.method_type = method_type
        self.payment_sum = payment_sum

    def to_dict_info(self):
        return {'date': self.start_date,
                'amount': self.payment_sum,
                'name': self.method_name,
                'method': self.method_type}

    def perform(self):
        payment_info = self.to_dict_info()
        self.device.make_payment(payment_info)

    def __repr__(self):
        return '%s - Making payment of sum %d using %s' % (self.start_date.time(), self.payment_sum, self.method_name)


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
        # Fail safe - generating fail call
        self._duration = timedelta(minutes=0, seconds=1)

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
            'operator': self.recipient_info['operator'],
            'phone_number': self.recipient_info['phone_number']
        }
        return call_info

    def perform(self):
        call_info = self.to_dict_info()
        status = self.device.make_call(call_info)
        if status == ServiceStatus.out_of_funds:
            self.handle_out_of_funds()

    def __repr__(self):
        return '%s - Outgoing call to %s, duration: %s' % (self.start_date.time(),
                                                           self.recipient_info['operator'], self.duration)


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
        status = self.device.use_internet(session_info)
        if status == ServiceStatus.out_of_funds:
            self.handle_out_of_funds()

    def __repr__(self):
        return '%s - Internet usage. Used %s mb, %s kb' % (self.start_date.time(), self.megabytes, self.kilobytes)

class Message(DeviceAction):
    def __init__(self, device, start_date, message_type, recipient_info):
        super().__init__(device, start_date)
        self.message_type = message_type
        self.recipient_info = recipient_info

    def to_dict_info(self):
        messsage_info = {
            'date': self.start_date,
            # 'name': self.message_type,
            'name': 'sms',  # FIXME: Change when other tariffs will be in system
            'operator': self.recipient_info['operator'],
            'phone_number': self.recipient_info['phone_number']
        }
        return messsage_info

    def perform(self):
        message_info = self.to_dict_info()
        status = self.device.send_message(message_info)
        if status == ServiceStatus.out_of_funds:
            self.handle_out_of_funds()

    def __repr__(self):
        return '%s - %s Message. Sent to %s' % (self.start_date.time(), self.message_type.swapcase(),
                                                self.recipient_info['operator'])


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
        status = self.device.ussd_request(service_info)
        if status == ServiceStatus.out_of_funds:
            self.handle_out_of_funds()

    def __repr__(self):
        return '%s - USSD request. Service: %s, code: %s' % (self.start_date.time(),
                                                             self.service_name, self.activation_code)


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
        status = self.device.ussd_request(tariff_info)
        if status == ServiceStatus.out_of_funds:
            self.handle_out_of_funds()

    def __repr__(self):
        return '%s - Changing tariff to %s' % (self.start_date.time(), self.tariff_name)


class LocationChange(DeviceAction):
    def __init__(self, device, start_date, new_location):
        super().__init__(device, start_date)
        self.new_location = new_location

    def to_dict_info(self):
        return {'date': self.start_date,
                'country': self.new_location['country'],
                'region': self.new_location['region']}

    def perform(self):
        location_info = self.to_dict_info()
        self.device.set_device_location(location_info)

    def __repr__(self):
        return '%s - Changing location to %s %s' % (self.start_date.time(),
                                                    self.new_location['country'], self.new_location['region'])
