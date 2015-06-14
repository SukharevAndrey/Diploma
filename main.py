from datetime import date, timedelta

from operator_simulation import MobileOperatorSimulator
from base import Base

def main():
    base_schema = Base.metadata
    simulator = MobileOperatorSimulator(base_schema)
    simulator.generate_static_data()
    simulator.generate_customers(date.today())
    simulator.simulate_period(date.today(), date.today())
    simulator.analyze_data(date.today(), date.today())

def main1():
    base_schema = Base.metadata
    simulator = MobileOperatorSimulator(base_schema)
    while True:
        print('Select action:')
        print('1. Fill database with static data')
        print('2. Generate customers and their devices')
        print('3. Simulate day')
        print('4. Analyze data')
        print('5. Clear all data')
        print('0. Exit')
        choice = input()
        if choice == '1':
            simulator.generate_static_data()
        elif choice == '2':
            simulator.generate_customers(date.today())
        elif choice == '3':
            simulator.simulate_period(date.today(), date.today())
        elif choice == '4':
            simulator.analyze_data(date.today())
        elif choice == '5':
            simulator.clear_all_data()
        elif choice == '0':
            return 0
        else:
            print('Wrong choice')

if __name__ == '__main__':
    main()
