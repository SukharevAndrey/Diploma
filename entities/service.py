import sqlalchemy as db
from sqlalchemy.orm import relationship
from base import Base


class Service(Base):
    __tablename__ = 'service'
    __mapper_args__ = {
        'polymorphic_on': 'type',
        'polymorphic_identity': 'service'
    }

    id = db.Column(db.Integer, primary_key=True)
    mobile_operator_id = db.Column(db.Integer, db.ForeignKey('mobileOperator.id'))

    name = db.Column(db.String, nullable=False)
    type = db.Column(db.String)
    description = db.Column(db.String)
    in_archive = db.Column(db.Boolean, default=False)
    activation_code = db.Column(db.String)
    deactivation_code = db.Column(db.String)

    operator = relationship('MobileOperator', uselist=False)
    tariffs = relationship('Tariff', secondary='tariffServices')
    packet = relationship('Packet', uselist=False)
    costs = relationship('Cost', secondary='serviceCost')


class Packet(Base):
    __tablename__ = 'packet'
    __table_args__ = (
        db.CheckConstraint("type IN ('voice', 'sms', 'mms', 'internet')"),
    )

    id = db.Column(db.Integer, primary_key=True)
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

    tariff_id = db.Column(db.Integer, db.ForeignKey('tariff.id'), primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), primary_key=True)


class DeviceService(Base):
    __tablename__ = 'deviceService'

    id = db.Column(db.Integer, primary_key=True)
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

    id = db.Column(db.Integer, primary_key=True)
    device_service_id = db.Column(db.Integer, db.ForeignKey('deviceService.id'))
    recipient_phone_number_id = db.Column(db.Integer, db.ForeignKey('phoneNumber.id'))
    device_location_id = db.Column(db.Integer, db.ForeignKey('location.id'))
    recipient_location_id = db.Column(db.Integer, db.ForeignKey('location.id'))

    use_date = db.Column(db.DateTime, default=db.func.now())
    amount = db.Column(db.Integer, default=1)

    device_location = relationship('Location', foreign_keys=[device_location_id], uselist=False)
    recipient_location = relationship('Location', foreign_keys=[recipient_location_id], uselist=False)
    recipient_phone_number = relationship('PhoneNumber', uselist=False)
    bill = relationship('Bill', uselist=False)


class Request(Base):
    __tablename__ = 'request'
    __table_args__ = (
        db.CheckConstraint("type IN ('activation', 'deactivation', 'status')"),
    )

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'))

    date = db.Column(db.DateTime, default=db.func.now())
    type = db.Column(db.String, default='activation')

    device = relationship('Device', uselist=False)
    service = relationship('Service', uselist=False)