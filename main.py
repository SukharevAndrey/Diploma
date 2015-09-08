from datetime import timedelta

from operator_simulation import MobileOperatorSimulator
from base import Base
from user_input import get_period, get_load_factor, get_clustering_algorithm


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


def main():
    base_schema = Base.metadata
    simulator = MobileOperatorSimulator(base_schema)
    period_start = None
    period_end = None
    algorithm = None
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
            if not algorithm:
                algorithm = get_clustering_algorithm()
            simulator.analyze_data(period_start, period_end, 'main', algorithm)
        elif choice == '5':
            if not period_start:
                period_start, period_end = get_period()
            factor = get_load_factor()
            simulator.generate_test_load(period_start, period_end, factor)
        elif choice == '6':
            if not period_start:
                period_start, period_end = get_period()
            if not algorithm:
                algorithm = get_clustering_algorithm()
            simulator.analyze_data(period_start, period_end, 'test', algorithm)
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
