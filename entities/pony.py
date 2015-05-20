from datetime import date
from datetime import time
from decimal import Decimal
from datetime import datetime
from pony.orm import *

db = Database("sqlite", ":memory:")

class Customer(db.Entity):
    id = PrimaryKey(int, auto=True)
    address = Required("GeographicAddress")
    agreements = Set("CustomerAgreement")
    credit_profile = Optional("CreditProfile")
    status = Required(str, default="active")
    rank = Required(int, default=1)


class Individual(db.Customer):
    """Main physical person info"""
    info = Required("IndividualInfo")


class Organization(db.Customer):
    """Main legal entity info"""
    vat_id = Required(str, unique=True)
    name = Required(str)
    branding_name = Required(str, nullable=True)


class CustomerAgreement(db.Entity):
    id = PrimaryKey(int, auto=True)
    customer = Optional(Customer)
    signed_agreement = Required("Agreement")
    sign_date = Required(date)
    period = Required(time)
    income_rating = Required(int)
    accounts = Set("Account")


class Service(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    description = Optional(str, nullable=True)
    in_archive = Required(bool, default=False)
    activation_code = Optional(str, nullable=True)
    deactivation_code = Optional(str, nullable=True)
    tariffs = Set("Tariff")
    device_services = Set("DeviceService")
    costs = Set("Cost")
    packet = Optional("Packet")
    device_requests = Set("Request")


class Tariff(db.Service):
    devices = Set("Device")
    services = Set(Service)


class Account(db.Entity):
    id = PrimaryKey(int, auto=True)
    calc_method = Required("CalculationMethod")
    agreement = Required(CustomerAgreement)
    credit_limit = Required(Decimal)
    trust_category = Required(int)
    bill_group = Required(int, default=0)
    devices = Set("Device")


class Device(db.Entity):
    id = PrimaryKey(int, auto=True)
    IMEI = Required(str, unique=True)
    type = Required(str, default="phone")
    account = Required(Account)
    tariff = Required(Tariff)
    services = Set("DeviceService")
    phone_number = Required("PhoneNumber")
    balances = Set("Balance")
    requests = Set("Request")


class Cost(db.Entity):
    id = PrimaryKey(int, auto=True)
    operator_from = Required("MobileOperator", reverse="costs_from")
    operator_to = Optional("MobileOperator", reverse="costs_to")
    use_cost = Required(Decimal, default=0)
    subscription_cost = Required(Decimal, default=0)
    services = Set(Service)


class CreditProfile(db.Entity):
    id = PrimaryKey(int, auto=True)
    date_created = Required(datetime)
    credit_risk_rating = Required(int)
    customer = Required(Customer)


class GeographicAddress(db.Entity):
    id = PrimaryKey(int, auto=True)
    house = Required("House")
    flat_num = Required(int)
    customers = Set(Customer)


class Country(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str, unique=True)
    iso2_code = Optional(str)
    iso3_code = Optional(str)
    capital = Required("Place")
    regions = Set("Region")
    mobile_operators = Set("MobileOperator")
    locations = Set("Location")


class Region(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    type = Required(str, default="oblast")
    code = Optional(str)
    country = Required(Country)
    places = Set("Place")
    mobile_operators = Set("MobileOperator")
    locations = Set("Location")


class Place(db.Entity):
    """May be town, village or some else place"""
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    region = Required(Region)
    districts = Set("District")
    capital_of = Optional(Country)
    born_individuals = Set("IndividualInfo")
    locations = Set("Location")


class District(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    place = Required(Place)
    streets = Set("Street")


class Street(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    district = Required(District)
    houses = Set("House")


class House(db.Entity):
    id = PrimaryKey(int, auto=True)
    number = Required(int)
    housing = Optional(str, nullable=True)
    street = Required(Street)
    customer_address = Optional(GeographicAddress)


class Packet(db.Entity):
    id = PrimaryKey(int, auto=True)
    type = Required(str, default="voice")
    amount = Required(int, default=0)
    service = Required(Service)


class Payment(db.Entity):
    id = PrimaryKey(int, auto=True)
    date = Required(datetime)
    balance = Required("Balance")
    amount = Required(Decimal, default=0)
    method = Required("PaymentMethod")


class PaymentMethod(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    description = Optional(str, nullable=True)
    payments = Set(Payment)


class Cash(db.PaymentMethod):
    cashier_info = Optional(str)


class CreditCard(db.PaymentMethod):
    number = Required(str, unique=True)
    name_on_card = Required(str)
    expiration_date = Required(date)


class ThirdParty(db.PaymentMethod):
    type = Required(str)


class DeviceService(db.Entity):
    id = PrimaryKey(int, auto=True)
    device = Required(Device)
    service = Required(Service)
    use_logs = Set("ServiceLog")
    is_blocked = Required(bool, default=False)
    is_activated = Required(bool, default=True)
    date_from = Required(datetime)
    date_to = Optional(datetime)
    packet_left = Optional(int, default=0)


class ServiceLog(db.Entity):
    id = PrimaryKey(int, auto=True)
    device_service = Required(DeviceService)
    use_date = Required(datetime)
    amount = Required(int, default=1)
    device_location = Optional("Location", reverse="service_logs_from")
    recipient_location = Optional("Location", reverse="service_logs_to")
    recipient_phone = Optional("PhoneNumber")
    bill = Optional("Bill")


class Balance(db.Entity):
    id = Required(int)
    type = Required(str, default="main")
    amount = Required(Decimal, default=0)
    due_date = Optional(datetime)
    paid_bills = Set("Bill")
    device = Optional(Device)
    payments = Set(Payment)
    PrimaryKey(id, type)


class CalculationMethod(db.Entity):
    id = PrimaryKey(int, auto=True)
    type = Required(str, default="advance")
    accounts = Set(Account)


class TermOrCondition(db.Entity):
    id = PrimaryKey(int, auto=True)
    description = Required(LongStr)
    agreements = Set("Agreement")


class PhoneNumber(db.Entity):
    """Phone numbers"""
    id = PrimaryKey(int, auto=True)
    type = Required(str, default="mobile")
    area_code = Required(str)
    number = Required(str)
    mobile_operator = Optional("MobileOperator")
    incoming_logs = Set(ServiceLog)
    device = Optional(Device)


class MobileOperator(db.Entity):
    """Mobile operators info"""
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    country = Optional(Country)
    region = Optional(Region)
    phone_numbers = Set(PhoneNumber)
    costs_from = Set(Cost, reverse="operator_from")
    costs_to = Set(Cost, reverse="operator_to")


class Agreement(db.Entity):
    id = PrimaryKey(int, auto=True)
    destination = Required(str)
    term_and_conditions = Set(TermOrCondition)
    latest_update = Required(date)
    customer_agreements = Set(CustomerAgreement)


class Bill(db.Entity):
    id = PrimaryKey(int, auto=True)
    service_info = Required(ServiceLog)
    date_created = Required(datetime)
    due_date = Optional(datetime)
    balance = Optional(Balance)
    paid = Required(Decimal, default=0)
    debt = Required(Decimal, default=0)


class Request(db.Entity):
    id = PrimaryKey(int, auto=True)
    date = Required(datetime)
    device = Required(Device)
    service = Optional(Service)
    type = Required(str, default="activation")


class IndividualInfo(db.Entity):
    id = PrimaryKey(int, auto=True)
    individual = Optional(Individual)
    gender = Required(str, default="male")
    first_name = Required(str)
    second_name = Optional(str, nullable=True)
    middle_name = Optional(str, nullable=True)
    birth_date = Required(date)
    birth_place = Required(Place)
    passport = Required(str, unique=True)
    nationality = Required(str)
    marital_status = Required(str)


class Location(db.Entity):
    id = PrimaryKey(int, auto=True)
    country = Optional(Country)
    region = Optional(Region)
    place = Optional(Place)
    service_logs_from = Set(ServiceLog, reverse="device_location")
    service_logs_to = Set(ServiceLog, reverse="recipient_location")