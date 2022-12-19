from sqlalchemy import Column, Integer, String
from src import db
import pytz
import datetime as dt

class Correction(db.Model):
    __tablename__ = 'corrections'
    id = db.Column(db.Integer, primary_key=True)
    sentence = db.Column(db.String(250), unique=False)
    #entity = db.Column(Entity, unique=False)
    #correction = db.Column(Entity, unique=False)
    timestamp = db.Column(db.DateTime, index=True, default=dt.datetime.utcnow)
    target = db.relationship('Entity', backref='entity', lazy='dynamic', nullable=False)
    correction = db.relationship('Entity', backref='correction', lazy='dynamic', nullable=False)


    def __init__(self, sentence=None, target=None, correction=None):
        self.sentence = sentence
        self.target = target
        self.correction = correction
        self.timestamp = dt.datetime.now(pytz.timezone('Europe/Helsinki'))

    def __repr__(self):
        return '<Correction %r -> %r (%r)>' % (self.entity, self.correction, self.timestamp)

class Entity(db.Model):
    __tablename__ = 'entities'
    id = db.Column(db.Integer, primary_key=True)
    string = db.Column(db.String(100), unique=False)
    type = db.Column(db.String(50), unique=False)
    location = db.Column(db.String(50), unique=False)
    correction_id = db.Column(db.Integer, db.ForeignKey('correction.id'), nullable=False)

    def __init__(self, string=None, type=None, location=None):
        self.string = string
        self.type = type
        self.location = location

    def __repr__(self):
        return '<Entity %r @ %r (%r)>' % (self.string, self.type, self.location)

def init_db():
    db.create_all()
