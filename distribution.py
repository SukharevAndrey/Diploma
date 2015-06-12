import numpy as np


class Distribution:
    def __init__(self, info):
        self.values_count = info['max_values']
        if 'values' not in info:
            self.values = [i for i in range(1, self.values_count+1)]
        else:
            self.values = info['values']
        # TODO: float32 instead of float64
        if 'probabilities' in info and info['probabilities']:
            self.p = np.array(info['probabilities'], dtype=np.float64)
        else:
            self.p = np.ones(self.values_count, dtype=np.float64)

        if len(self.p) < self.values_count:
            self.p = np.concatenate((self.p, np.zeros(self.values_count-len(self.p))))

        self.normalize()

    @staticmethod
    def from_list(values_list):
        # TODO: Refactor from distributions_from_list
        return 1

    @staticmethod
    def from_dict(values_dict):
        return 1

    def normalize(self):
        # TODO: Handle situation when sum is not 1 (due to float error)
        sum_p = np.sum(self.p)
        self.p /= sum_p

    def get_value(self, n=1, return_array=True):
        if return_array:
            return np.random.choice(self.values, size=n, p=self.p)
        else:
            return np.random.choice(self.values, p=self.p)
