import sqlalchemy as db
from sqlalchemy.orm import relationship
from base import Base


class Customer(Base):
    __tablename__ = 'customer'
    __mapper_args__ = {
        'polymorphic_on': 'type'
    }

    id = db.Column(db.Integer, primary_key=True, index=True)
    geographic_address_id = db.Column(db.Integer, db.ForeignKey('geographicAddress.id'))

    date_from = db.Column(db.DateTime, default=db.func.now())
    date_to = db.Column(db.DateTime)
    type = db.Column(db.String)
    status = db.Column(db.String, default='active')
    rank = db.Column(db.Integer, default=1)

    address = relationship('GeographicAddress', uselist=False, backref='customers')
    agreements = relationship('CustomerAgreement')
    credit_profile = relationship('CreditProfile', uselist=False)


class CreditProfile(Base):
    __tablename__ = 'creditProfile'

    id = db.Column(db.Integer, primary_key=True, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))

    date_created = db.Column(db.DateTime, default=db.func.now())
    credit_risk_rating = db.Column(db.Integer, default=0)

    customer = relationship('Customer')


class Individual(Customer):
    __tablename__ = 'individual'
    __mapper_args__ = {
        'polymorphic_identity': 'individual'
    }

    id = db.Column(db.Integer, db.ForeignKey('customer.id'), primary_key=True)
    info_id = db.Column(db.Integer, db.ForeignKey('individualInfo.id'))

    info = relationship('IndividualInfo', uselist=False)


class IndividualInfo(Base):
    __tablename__ = 'individualInfo'
    __table_args__ = (
        db.CheckConstraint("gender IN ('male', 'female')"),
        db.CheckConstraint("marital_status IN ('single', 'married')"),
    )

    id = db.Column(db.Integer, primary_key=True, index=True)

    first_name = db.Column(db.String, nullable=False)
    second_name = db.Column(db.String)
    middle_name = db.Column(db.String)

    gender = db.Column(db.String, default='male')
    birth_date = db.Column(db.Date)
    birth_place = db.Column(db.String)  # TODO: Link to place
    passport = db.Column(db.String, unique=True)
    nationality = db.Column(db.String)
    marital_status = db.Column(db.String)


class Organization(Customer):
    __tablename__ = 'organization'
    __mapper_args__ = {
        'polymorphic_identity': 'organization'
    }

    id = db.Column(db.Integer, db.ForeignKey('customer.id'), primary_key=True, index=True)

    vat_id = db.Column(db.String, nullable=False, unique=True)
    name = db.Column(db.String, nullable=False)
    branding_name = db.Column(db.String)


class Agreement(Base):
    __tablename__ = 'agreement'

    id = db.Column(db.Integer, primary_key=True, index=True)
    destination = db.Column(db.String, nullable=False)
    latest_update = db.Column(db.Date, default=db.func.now())

    terms_and_conditions = relationship('TermOrCondition',
                                        secondary='agreementTermsAndConditions')


class TermOrCondition(Base):
    __tablename__ = 'termOrCondition'

    id = db.Column(db.Integer, primary_key=True, index=True)
    description = db.Column(db.String)

    agreements = relationship('Agreement',
                              secondary='agreementTermsAndConditions')


class AgreementTermOrCondition(Base):
    __tablename__ = 'agreementTermsAndConditions'
    agreement_id = db.Column(db.Integer, db.ForeignKey('agreement.id'), primary_key=True)
    condition_id = db.Column(db.Integer, db.ForeignKey('termOrCondition.id'), primary_key=True)


class CustomerAgreement(Base):
    __tablename__ = 'customerAgreement'

    id = db.Column(db.Integer, primary_key=True, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    agreement_id = db.Column(db.Integer, db.ForeignKey('agreement.id'))

    sign_date = db.Column(db.Date, default=db.func.now())
    date_to = db.Column(db.Date)
    income_rating = db.Column(db.Integer, default=0)

    customer = relationship('Customer')
    accounts = relationship('Account')
    signed_agreement = relationship('Agreement')


class CalculationMethod(Base):
    __tablename__ = 'calculationMethod'
    __table_args__ = (
        db.CheckConstraint("type IN ('advance', 'credit')"),
    )

    id = db.Column(db.Integer, primary_key=True, index=True)
    type = db.Column(db.String, default='advance')

    accounts = relationship('Account')


class Account(Base):
    __tablename__ = 'account'

    id = db.Column(db.Integer, primary_key=True, index=True)
    agreement_id = db.Column(db.Integer, db.ForeignKey('customerAgreement.id'))
    calculation_method_id = db.Column(db.Integer, db.ForeignKey('calculationMethod.id'))

    date_from = db.Column(db.DateTime, default=db.func.now())
    date_to = db.Column(db.DateTime)

    credit_limit = db.Column(db.Numeric, default=0)
    trust_category = db.Column(db.Integer, default=0)
    bill_group = db.Column(db.Integer, default=0)

    agreement = relationship('CustomerAgreement', uselist=False)
    calc_method = relationship('CalculationMethod', uselist=False)
    devices = relationship('Device')


class Device(Base):
    __tablename__ = 'device'
    __table_args__ = (
        db.CheckConstraint("type IN ('phone', 'smartphone', 'tablet', 'modem')"),
    )

    id = db.Column(db.Integer, primary_key=True, index=True)
    phone_number_id = db.Column(db.Integer, db.ForeignKey('phoneNumber.id'))
    tariff_id = db.Column(db.Integer, db.ForeignKey('tariff.id'))
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))

    date_registered = db.Column(db.DateTime, default=db.func.now())
    IMEI = db.Column(db.String, unique=True)
    type = db.Column(db.String, default='phone')

    account = relationship('Account', uselist=False)
    phone_number = relationship('PhoneNumber', uselist=False)
    tariff = relationship('Tariff', uselist=False)

    balances = relationship('Balance')
    services = relationship('DeviceService')
    requests = relationship('Request')
    locations = relationship('Location')

