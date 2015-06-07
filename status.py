from enum import Enum


class ServiceStatus(Enum):
    success = 1
    out_of_funds = 2
    fail = 3
