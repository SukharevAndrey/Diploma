import string
import random
from datetime import date, timedelta

from entities.customer import Individual, IndividualInfo, Organization

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


def random_gender():
    return random.choice(['male', 'female'])


def random_marital_status():
    return random.choice(['single', 'married'])


def random_birth_date(current_date, age):
    # TODO: Proper leap year handling
    days = age*366
    days += random.randint(-350, 350)
    return current_date+timedelta(days=-days)


def random_individual(current_date, age):
    gender = random_gender()
    first_name, second_name, middle_name = random_credentials(gender)

    info = IndividualInfo(first_name=first_name,
                          second_name=second_name,
                          middle_name=middle_name,
                          gender=gender,
                          birth_date=random_birth_date(current_date, age),
                          birth_place='Moscow',
                          passport=random_passport(),
                          nationality='russian',
                          marital_status=random_marital_status())

    individual = Individual(date_from=current_date, info=info)

    return individual


def random_VAT():
    return ''.join(map(str, [random.randint(0, 9) for _ in range(12)]))


def random_organization(current_date):
    organization = Organization(date_from=current_date,
                                name=random_string(),
                                vat_id=random_VAT(),
                                branding_name=random_string())
    return organization


def random_IMEI():
    return ''.join(map(str, [random.randint(0, 9) for _ in range(15)]))
