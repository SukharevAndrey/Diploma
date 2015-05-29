from abc import ABCMeta, abstractmethod


class IntersectionError(Exception):
    pass


class Action(metaclass=ABCMeta):
    def __init__(self, customer, start_date):
        self.customer = customer
        self.start_date = start_date

    @abstractmethod
    def to_dict_info(self):
        pass

    @abstractmethod
    def perform(self):
        print('Performing action')


class DeviceAction(Action):
    def __init__(self, customer, device, start_date):
        super().__init__(customer, start_date)
        self._device = device

    @property
    def device(self):
        return self._device


class Call(DeviceAction):
    def __init__(self, customer, device, start_date, maximum_duration):
        super().__init__(customer, device, start_date)
        self._duration = None
        self.end_date = None
        self.maximum_duration = maximum_duration

    @property
    def duration(self):
        return self._duration

    @duration.setter
    def duration(self, duration):
        if duration < self.maximum_duration:
            self._duration = duration
            self.end_date = self.start_date+duration
        else:
            raise IntersectionError('call intersects with next one')

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
        super().perform()
        call_info = self.to_dict_info()
        self.customer.make_call(self.device, call_info)

    def __repr__(self):
        return '%s - Outgoing call, duration: %s'%(self.start_date.time(), self.duration)


class Internet(DeviceAction):
    def __init__(self, customer, device, start_date, end_date=None):
        super().__init__(customer, device, start_date)
        self.end_date = end_date
        self._megabytes = 0
        self._kilobytes = 0

    @property
    def megabytes(self):
        return self._megabytes

    @property
    def kilobytes(self):
        return self._kilobytes

    def to_dict_info(self):
        return {}

    def perform(self):
        super().perform()

    def __repr__(self):
        return '%s - Internet usage. Used %s mb, %s kb'%(self.start_date.time(), self.megabytes, self.kilobytes)
