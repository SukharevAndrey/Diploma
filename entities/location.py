import sqlalchemy as db
from sqlalchemy.orm import relationship
from base import Base


class Country(Base):
    __tablename__ = 'country'
    __table_args__ = (db.Index('idx_country_id_name', "id", "name"),)

    id = db.Column(db.Integer, primary_key=True, index=True)
    capital_id = db.Column(db.Integer, db.ForeignKey('place.id'))

    name = db.Column(db.String, nullable=False)
    iso2_code = db.Column(db.String)
    iso3_code = db.Column(db.String)

    regions = relationship('Region')
    capital = relationship('Place', uselist=False)


class Region(Base):
    __tablename__ = 'region'
    __table_args__ = (db.Index('ix_region_name_country_id', "name", "country_id"),)

    id = db.Column(db.Integer, primary_key=True, index=True)
    country_id = db.Column(db.Integer, db.ForeignKey('country.id', use_alter=True))

    name = db.Column(db.String, nullable=False)
    type = db.Column(db.String, default='oblast')
    code = db.Column(db.String)
    country = relationship('Country', uselist=False)
    operators = relationship('MobileOperator')


class Place(Base):
    __tablename__ = 'place'

    id = db.Column(db.Integer, primary_key=True, index=True)
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'))

    name = db.Column(db.String, nullable=False)

    region = relationship('Region', uselist=False)
    capital_of = relationship('Country', uselist=False)


class District(Base):
    __tablename__ = 'district'

    id = db.Column(db.Integer, primary_key=True, index=True)
    place_id = db.Column(db.Integer, db.ForeignKey('place.id'))

    name = db.Column(db.String, nullable=False)
    place = relationship('Place', uselist=False)


class Street(Base):
    __tablename__ = 'street'

    id = db.Column(db.Integer, primary_key=True, index=True)
    district_id = db.Column(db.Integer, db.ForeignKey('district.id'))

    name = db.Column(db.String, nullable=False)
    district = relationship('District', uselist=False)


class House(Base):
    __tablename__ = 'house'

    id = db.Column(db.Integer, primary_key=True, index=True)
    street_id = db.Column(db.Integer, db.ForeignKey('street.id'))

    number = db.Column(db.Integer, nullable=False)
    housing = db.Column(db.String)

    street = relationship('Street', uselist=False)


class GeographicAddress(Base):
    __tablename__ = 'geographicAddress'

    id = db.Column(db.Integer, primary_key=True, index=True)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'))

    flat_num = db.Column(db.Integer)
    house = relationship('House', uselist=False)


class Location(Base):
    __tablename__ = 'location'

    id = db.Column(db.Integer, primary_key=True, index=True)
    country_id = db.Column(db.Integer, db.ForeignKey('country.id'))
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'))
    place_id = db.Column(db.Integer, db.ForeignKey('place.id'))
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'))

    date_from = db.Column(db.DateTime, default=db.func.now())
    date_to = db.Column(db.DateTime)

    country = relationship('Country', uselist=False)
    region = relationship('Region', uselist=False)
    place = relationship('Place', uselist=False)

    device = relationship('Device', uselist=False)
