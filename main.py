from datetime import date

from operator_simulation import MobileOperatorSimulator
from base import Base

def main():
    base_schema = Base.metadata
    simulator = MobileOperatorSimulator(base_schema)
    simulator.initial_fill()
    simulator.simulate_day(date.today())
    # simulator.analyze_data(date.today())

# def main():
#     base_schema = Base.metadata
#     simulator = MobileOperatorSimulator(base_schema)
#     while True:
#         print('Select action:')
#         print('1. Fill database with static data')
#         print('2. Simulate day')
#         print('3. Analyze data')
#         print('4. Clear all data')
#         print('0. Exit')
#         choice = input()
#         if choice == '1':
#             simulator.initial_fill()
#         elif choice == '2':
#             simulator.simulate_day(date.today())
#         elif choice == '3':
#             simulator.analyze_data(date.today())
#         elif choice == '4':
#             simulator.clear_all_data()
#         elif choice == '0':
#             return 0
#         else:
#             print('Wrong choice')

if __name__ == '__main__':
    main()
