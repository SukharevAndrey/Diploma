from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from base import Base
from generator import MobileOperatorGenerator

POOL_SIZE = 20


class MobileOperatorSimulator:
    def __init__(self, metadata):
        self.metadata = metadata
        self.db1_engine = create_engine('sqlite:///:memory:', pool_size=POOL_SIZE, echo=False)
        self.db2_engine = None

        self.generate_schema(self.db1_engine)
        # self.generate_schema(self.db2_engine)

        self.db1_session = scoped_session(sessionmaker(bind=self.db1_engine))
        # self.db2_session = scoped_session(sessionmaker(bind=self.db2_engine))

        self.initial_balance = 200
        # self.initial_fill()

    def generate_schema(self, engine):
        self.metadata.create_all(engine)

    def initial_fill(self):
        gen = MobileOperatorGenerator(verbose=True)
        gen.generate_static_data(self.db1_session)


class SimulatedCustomer:
    def __init__(self, behavior_info):
        pass

    def sign_agreement(self):
        pass

    def register_account(self, agreement):
        pass

    def add_device(self, account):
        pass

    def change_tariff(self, device, new_tariff_name):
        pass

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

    def begin_simulation(self):
        pass

    def simulate_day(self):
        pass


def main():
    sim = MobileOperatorSimulator(Base.metadata)
    sim.initial_fill()


if __name__ == '__main__':
    main()
