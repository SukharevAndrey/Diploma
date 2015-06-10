import sqlalchemy as db
from sqlalchemy.orm import relationship
from base import Base


class Service(Base):
    __tablename__ = 'service'
    __mapper_args__ = {
        'polymorphic_on': 'type',
        'polymorphic_identity': 'service'
    }

    id = db.Column(db.Integer, primary_key=True, index=True)
    mobile_operator_id = db.Column(db.Integer, db.ForeignKey('mobileOperator.id'))

    name = db.Column(db.String, nullable=False, index=True)
    type = db.Column(db.String)
    description = db.Column(db.String)
    in_archive = db.Column(db.Boolean, default=False)

    activation_code = db.Column(db.String, index=True)
    activation_cost = db.Column(db.Numeric, default=0)
    deactivation_code = db.Column(db.String)
    duration_days = db.Column(db.Integer, default=0)

    operator = relationship('MobileOperator', uselist=False)
    tariffs = relationship('Tariff', secondary='tariffServices')
    packet = relationship('Packet', uselist=False)
    costs = relationship('Cost')


class Packet(Base):
    __tablename__ = 'packet'
    __table_args__ = (
        db.CheckConstraint("type IN ('outgoing_call', 'sms', 'mms', 'internet')"),
    )

    id = db.Column(db.Integer, primary_key=True, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'))

    type = db.Column(db.String, nullable=False)
    amount = db.Column(db.Integer, default=0)


class Tariff(Service):
    __tablename__ = 'tariff'
    __mapper_args__ = {
        'polymorphic_identity': 'tariff'
    }
    id = db.Column(db.Integer, db.ForeignKey('service.id'), primary_key=True)

    prepaid_only = db.Column(db.Boolean, default=False)
    postpaid_only = db.Column(db.Boolean, default=False)

    attached_services = relationship('Service', secondary='tariffServices')
    devices = relationship('Device')


class TariffServices(Base):
    __tablename__ = 'tariffServices'
    __table_args__ = (db.Index("ix_tariff_services_ids", "tariff_id", "service_id"),)

    tariff_id = db.Column(db.Integer, db.ForeignKey('tariff.id'), primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), primary_key=True)


class DeviceService(Base):
    __tablename__ = 'deviceService'

    id = db.Column(db.Integer, primary_key=True, index=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'))

    is_blocked = db.Column(db.Boolean, default=False)
    is_activated = db.Column(db.Boolean, default=True)
    date_from = db.Column(db.DateTime, default=db.func.now())
    date_to = db.Column(db.DateTime)
    packet_left = db.Column(db.Integer, default=0)

    device = relationship('Device', uselist=False)
    service = relationship('Service', uselist=False)


class ServiceLog(Base):
    __tablename__ = 'serviceLog'
    __table_args__ = (
        db.CheckConstraint("action_type IN ('usage', 'activation', 'deactivation', 'blocking', 'unlocking')"),
    )

    id = db.Column(db.Integer, primary_key=True, index=True)
    device_service_id = db.Column(db.Integer, db.ForeignKey('deviceService.id'))
    recipient_phone_number_id = db.Column(db.Integer, db.ForeignKey('phoneNumber.id'))
    recipient_location_id = db.Column(db.Integer, db.ForeignKey('location.id'))

    use_date = db.Column(db.DateTime, default=db.func.now())
    action_type = db.Column(db.String, default='usage')
    amount = db.Column(db.Integer, default=1)

    device_service = relationship('DeviceService', uselist=False)
    recipient_location = relationship('Location', uselist=False)
    recipient_phone_number = relationship('PhoneNumber', uselist=False)
    bill = relationship('Bill', uselist=False)


class Request(Base):
    __tablename__ = 'request'
    __table_args__ = (
        db.CheckConstraint("type IN ('activation', 'deactivation', 'status')"),
    )

    # TODO: Implicit, explicit

    id = db.Column(db.Integer, primary_key=True, index=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'))
    tariff_id = db.Column(db.Integer, db.ForeignKey('tariff.id'))

    date_created = db.Column(db.DateTime, default=db.func.now())
    type = db.Column(db.String, default='activation')
    request_type = db.Column(db.String)

    device = relationship('Device', uselist=False)
    service = relationship('Service', foreign_keys=[service_id], uselist=False)
    tariff = relationship('Tariff', foreign_keys=[tariff_id], uselist=False)
