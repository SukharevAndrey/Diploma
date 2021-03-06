import sqlalchemy as db
from sqlalchemy.orm import relationship
from base import Base


class Balance(Base):
    __tablename__ = 'balance'
    __table_args__ = (
        db.CheckConstraint("type IN ('advance', 'credit', 'discount')"),
    )

    id = db.Column(db.Integer, primary_key=True, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))

    date_from = db.Column(db.DateTime, default=db.func.now())
    date_to = db.Column(db.DateTime)

    type = db.Column(db.String, default='advance')
    amount = db.Column(db.Numeric, default=0)

    account = relationship('Account', uselist=False)
    payments = relationship('Payment')
    paid_bills = relationship('Bill')


class Bill(Base):
    __tablename__ = 'bill'

    id = db.Column(db.Integer, primary_key=True, index=True)
    service_log_id = db.Column(db.Integer, db.ForeignKey('serviceLog.id'))
    balance_id = db.Column(db.Integer, db.ForeignKey('balance.id'))

    date_from = db.Column(db.DateTime, default=db.func.now())
    date_to = db.Column(db.DateTime)

    due_date = db.Column(db.DateTime)
    paid = db.Column(db.Numeric, default=0)
    debt = db.Column(db.Numeric, default=0)

    service_log = relationship('ServiceLog', uselist=False)
    balance = relationship('Balance', uselist=False)


class Payment(Base):
    __tablename__ = 'payment'

    id = db.Column(db.Integer, primary_key=True, index=True)
    balance_id = db.Column(db.Integer, db.ForeignKey('balance.id'))
    method_id = db.Column(db.Integer, db.ForeignKey('paymentMethod.id'))

    amount = db.Column(db.Numeric, default=0)
    date = db.Column(db.DateTime, default=db.func.now())

    balance = relationship('Balance', uselist=False)
    method = relationship('PaymentMethod', foreign_keys=[method_id], uselist=False)


class PaymentMethod(Base):
    __tablename__ = 'paymentMethod'
    __mapper_args__ = {
        'polymorphic_on': 'type'
    }

    id = db.Column(db.Integer, primary_key=True, index=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id', use_alter=True))

    type = db.Column(db.String)
    name = db.Column(db.String)
    description = db.Column(db.String)


class CreditCard(PaymentMethod):
    __tablename__ = 'creditCard'
    __mapper_args__ = {
        'polymorphic_identity': 'credit_card'
    }

    id = db.Column(db.Integer, db.ForeignKey('paymentMethod.id'), primary_key=True, index=True)
    number = db.Column(db.String, nullable=False, unique=True)
    name_on_card = db.Column(db.String, nullable=False)
    expiration_date = db.Column(db.Date, nullable=False)


class Cash(PaymentMethod):
    __tablename__ = 'cash'
    __mapper_args__ = {
        'polymorphic_identity': 'cash'
    }

    id = db.Column(db.Integer, db.ForeignKey('paymentMethod.id'), primary_key=True)
    cashier_info = db.Column(db.String)


class ThirdPartyCollection(PaymentMethod):
    __tablename__ = 'thirdPartyCollection'
    __mapper_args__ = {
        'polymorphic_identity': 'third_party'
    }

    id = db.Column(db.Integer, db.ForeignKey('paymentMethod.id'), primary_key=True)


class Cost(Base):
    __tablename__ = 'cost'
    __table_args__ = (
        db.Index("ix_cost_from_to", "operator_from_id", "operator_to_id"),
    )

    id = db.Column(db.Integer, primary_key=True, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), index=True)
    operator_from_id = db.Column(db.Integer, db.ForeignKey('mobileOperator.id'))
    operator_to_id = db.Column(db.Integer, db.ForeignKey('mobileOperator.id'))

    use_cost = db.Column(db.Numeric, default=0)
    subscription_cost = db.Column(db.Numeric, default=0)

    operator_from = relationship('MobileOperator', foreign_keys=[operator_from_id], uselist=False)
    operator_to = relationship('MobileOperator', foreign_keys=[operator_to_id], uselist=False)
    service = relationship('Service', uselist=False)
