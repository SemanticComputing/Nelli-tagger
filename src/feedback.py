import logging, json
import argparse
import sys, os
import urllib
from flask_restful import reqparse
import traceback
from flask import request

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('core')

def validate_correction():
    pass

def parse_feedback_params():
    logger.info("REG.ARGS, %s", request.args)
    parser = reqparse.RequestParser()
    parser.add_argument('sentence')
    parser.add_argument('entity')
    parser.add_argument('correction')
    args = parser.parse_args()
    logger.info("ARGS, %s", args)
    print("ARGS ", args)

    feedback = dict()

    if 'sentence' in args:
        if args['sentence'] != None:
            feedback['sentence'] = args['sentence']
    if 'entity' in args:
        e = Entity()
        if args['entity'] != None:
            if e.parse(args['entity']) == True:
                feedback['entity'] = e
    if 'correction' in args:
        e = Entity()
        if args['correction'] != None:
            if e.parse(args['correction']) == True:
                feedback['correction'] = e

    return feedback

class Entity():
    def __init__(self):
        self.name = ""
        self.type = ""
        self.location = ""

    def parse(self, entity_string):
        entity_arr = entity_string.split(',')
        if len(entity_arr) == 3:
            self.name = entity_arr[0]
            self.type = entity_arr[1]
            self.location = entity_arr[2]
        else:
            return False
        return True

    def get_name(self):
        return self.name

    def get_type(self):
        return self.type

    def get_location(self):
        return self.location

    def __repr__(self):
        return str(self.name) + "(type=" + str(self.type) + ", location=" + str(self.location) + ")"