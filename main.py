from operator_simulation import MobileOperatorSimulator
from base import Base

def main():
    base_schema = Base.metadata
    simulator = MobileOperatorSimulator(base_schema)
    simulator.initial_fill()
    simulator.begin_simulation()

if __name__ == '__main__':
    main()
