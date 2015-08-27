from datetime import date, timedelta

from operator_simulation import MobileOperatorSimulator
from base import Base

def main1():
    base_schema = Base.metadata
    simulator = MobileOperatorSimulator(base_schema)
    simulator.generate_static_data()
    simulator.generate_customers(date.today()-timedelta(days=1))
    simulator.simulate_period(date.today(), date.today())
    simulator.analyze_data(date.today(), date.today())
    simulator.generate_test_load(date.today(), date.today(), 0.2)


def print_menu():
    print('Select action:')
    print('1. Fill database with static data')
    print('2. Generate customers and their devices')
    print('3. Simulate period')
    print('4. Analyze main base')
    print('5. Copy decreased activity')
    print('6. Analyze test base')
    print('7. Clear main base data')
    print('8. Clean test base data')
    print('9. Change period')
    print('0. Exit')


def input_to_date(user_input):
    if not user_input:
        return date.today()
    day, month, year = map(int, user_input.split('-'))
    return date(year, month, day)


def get_period():
    while True:
        start_date = input('Enter simulation period start: ')
        period_start = input_to_date(start_date)
        end_date = input('Enter simulation period end: ')
        period_end = input_to_date(end_date)
        if period_start <= period_end:
            return period_start, period_end
        else:
            print('Incorrect period')


def get_load_factor():
    while True:
        raw_factor = input('Enter load factor (in percent): ')
        try:
            factor = float(raw_factor)
            return factor/100
        except ValueError:
            print('Incorrect factor')
            continue


def main():
    base_schema = Base.metadata
    simulator = MobileOperatorSimulator(base_schema)
    period_start = None
    period_end = None
    while True:
        print_menu()
        choice = input()
        if choice == '1':
            simulator.generate_static_data()
        elif choice == '2':
            if not period_start:
                period_start, period_end = get_period()
            simulator.generate_customers(period_start-timedelta(days=1))
        elif choice == '3':
            if not period_start:
                period_start, period_end = get_period()
            simulator.simulate_period(period_start, period_end)
        elif choice == '4':
            if not period_start:
                period_start, period_end = get_period()
            simulator.analyze_data(period_start, period_end, base_type='main')
        elif choice == '5':
            if not period_start:
                period_start, period_end = get_period()
            factor = get_load_factor()
            simulator.generate_test_load(period_start, period_end, factor)
        elif choice == '6':
            if not period_start:
                period_start, period_end = get_period()
            simulator.analyze_data(period_start, period_end, base_type='test')
        elif choice == '7':
            simulator.clear_main_base_data()
        elif choice == '8':
            simulator.clear_test_base_data()
        elif choice == '9':
            period_start, period_end = get_period()
        elif choice == '0':
            return 0
        else:
            print('Wrong choice')

if __name__ == '__main__':
    main()
