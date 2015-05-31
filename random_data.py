import string
import random
from datetime import date

from entities.customer import Individual, IndividualInfo, Device

used_IMEI = set()

month_days = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
              7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}


def random_string(min_len=4, max_len=10):
    return ''.join(random.choice(string.ascii_lowercase)
                   for _ in range(random.randint(min_len, max_len+1)))


def random_credentials(gender):
    first_name = random_string().capitalize()
    second_name = random_string().capitalize()
    middle_name = random_string().capitalize()
    return first_name, second_name, middle_name


def random_date(min_year=1930, max_year=2015):
    year = random.randint(min_year, max_year)
    month = random.randint(1, 12)
    day = random.randint(1, month_days[month])
    return date(year, month, day)


def random_passport():
    series = random.randint(1000, 9999)
    number = random.randint(100000, 999999)
    return '%d %d' % (series, number)


def random_individual():
    gender = random.choice(('male', 'female'))
    marital_status = random.choice(('single', 'married'))

    first_name, second_name, middle_name = random_credentials(gender)

    info = IndividualInfo(first_name=first_name,
                          second_name=second_name,
                          middle_name=middle_name,
                          gender=gender,
                          birth_date=random_date(),
                          birth_place='Moscow',
                          passport=random_passport(),
                          nationality='russian',
                          marital_status=marital_status)

    individual = Individual(info=info)

    return individual

def random_IMEI():
    return ''.join(map(str, [random.randint(0, 9) for i in range(15)]))