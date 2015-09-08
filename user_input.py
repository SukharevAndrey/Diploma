from datetime import date
from analyzer import ClusteringAlgorithm


def input_to_date(user_input):
    if not user_input:
        return date.today()
    day, month, year = map(int, user_input.split('-'))
    return date(year, month, day)


def get_period():
    while True:
        start_date = input('Enter simulation period start (default - today): ')
        period_start = input_to_date(start_date)
        end_date = input('Enter simulation period end (default - today): ')
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


def get_clustering_algorithm():
    while True:
        raw_algorithm = input('Enter clustering algorithm (K-Means, DBSCAN, BIRCH): ')
        if raw_algorithm == 'K-Means':
            return ClusteringAlgorithm(raw_algorithm)
        elif raw_algorithm == 'DBSCAN':
            selected_algorithm = ClusteringAlgorithm(raw_algorithm)
            try:
                eps = float(input('Enter epsilon (floating point number): '))
                selected_algorithm.params['eps'] = eps
                return selected_algorithm
            except ValueError:
                print('Incorrect value')
                continue
        elif raw_algorithm == 'BIRCH':
            selected_algorithm = ClusteringAlgorithm(raw_algorithm)
            raw_threshold = input('Enter threshold (radius of subcluster, default - 0.5): ')
            threshold = 0.5
            try:
                threshold = float(raw_threshold)
            except ValueError:
                if raw_threshold:
                    print('Incorrect value')
                    continue
            selected_algorithm.params['threshold'] = threshold
            raw_branching = input('Enter branching factor (default - 50): ')
            branching_factor = 50
            try:
                branching_factor = int(raw_branching)
            except ValueError:
                if raw_branching:
                    print('Incorrect value')
                    continue
            selected_algorithm.params['branching'] = branching_factor
            return selected_algorithm
        else:
            print('Incorrect algorithm')
            continue
