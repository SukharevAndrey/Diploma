import sqlalchemy as db
from sqlalchemy.orm import relationship
from base import Base


class MobileOperator(Base):
    __tablename__ = 'mobileOperator'
    __table_args__ = (
        db.Index('ix_operator_name_country_region', "name", "country_id", "region_id"),
    )

    id = db.Column(db.Integer, primary_key=True, index=True)
    country_id = db.Column(db.Integer, db.ForeignKey('country.id'))
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'))

    name = db.Column(db.String, nullable=False)
    country = relationship('Country', uselist=False)
    region = relationship('Region', uselist=False)

    tariffs = relationship('Tariff')
    services = relationship('Service')


class PhoneNumber(Base):
    __tablename__ = 'phoneNumber'
    __table_args__ = (
        db.CheckConstraint("type IN ('fixed', 'mobile')"),
        db.Index("ix_phone_number", "area_code", "number")
    )

    id = db.Column(db.Integer, primary_key=True, index=True)
    mobile_operator_id = db.Column(db.Integer, db.ForeignKey('mobileOperator.id'))

    type = db.Column(db.String, default='mobile')
    area_code = db.Column(db.String, nullable=False)
    number = db.Column(db.String, nullable=False)

    device = relationship('Device', uselist=False)
    mobile_operator = relationship('MobileOperator', uselist=False)
