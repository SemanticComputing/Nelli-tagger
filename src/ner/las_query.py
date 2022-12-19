'''
Created on 17.2.2016

@author: Claire
'''
import urllib, codecs
from requests import Request, Session
import requests, json
import logging
import json, traceback, sys
from flask import abort
import configparser
from configparser import Error, ParsingError, MissingSectionHeaderError, NoOptionError, DuplicateOptionError, DuplicateSectionError, NoSectionError
from distutils.util import strtobool

# logging setup
logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('las')

class lasQuery:
    def __init__(self, file_name_pattern="", path="", full_path=""):
        self.__file_name_pattern = file_name_pattern
        self.__path = path
        self.query_string_cache = dict()
        self.base_url, self.lemmatize = self.read_configs('LAS')

    def read_configs(self, env):
        tool = ""
        lemmatize = False

        try:
            config = configparser.ConfigParser()
            config.read('confs/services.ini')

            if env in config:
                tool = config[env]['url']
                lemmatize = strtobool(config[env]['lemmatize'])
            else:
                err_msg = 'The environment is not set: %s' % (env)
                raise Exception(err_msg)
        except Error:
            logger.warning("[ERROR] ConfigParser error:", sys.exc_info()[0])
            traceback.print_exc()
            abort(500)
        except Exception:
            logger.warning("[ERROR] Unexpected error:", sys.exc_info()[0])
            traceback.print_exc()
            abort(500)

        return tool, lemmatize
        
    def analysis(self, input):
        res = " "
        j = self.morphological_analysis(input)

        for w in j:
            analysis = w['analysis']
            for r in analysis:
                wp = r['wordParts']
                for part in wp:
                    lemma = part['lemma']
                    upos=""
                    if 'tags' in part:
                        p = part['tags']
                        if 'UPOS' in p:
                            p1 = p['UPOS']
                            if len(p1)>0:
                                upos = part['tags']['UPOS'][0]
                    if upos == 'NOUN' or upos == 'PROPN':
                        if len(wp) > 1:
                            res = res + lemma
                        else:
                            res = res + lemma + " "
                
        return res

    #morphological_analysis    
    def morphological_analysis(self,input):
        
        # do POST
        url = self.render_url('las/analyze')
        params = {'text': input, 'locale':'fi', "forms":"V+N+Nom+Sg"}
        data = urllib.parse.urlencode(params).encode()
        
        content =  None
        content = self.prepared_request_morphological(input)
        if content == None:
            return ""
        return content.json()
    
    def lexical_analysis(self,input, lang):
        result = ""

        # do POST
        url = self.render_url('las/baseform')
        params = {'text': input, 'locale': lang}

        if input not in self.query_string_cache.keys():
            content =  None
            content = self.prepared_request(input, lang)
            if content == None:
                return ""

            result = content.content.decode('utf-8')
            if result.startswith('"'):
                result = result[1:]
            if result.endswith('"'):
                result = result[:-1]

            # add to cache
            self.query_string_cache[input] = result
        else:
            result = self.query_string_cache[input]

        return result
    
    def prepared_request(self, input, lang):
        s = Session()

        url = self.render_url('las/baseform')
        params = {'text': input, 'locale' : lang}
        logger.info("[LAS] prepared_request: %s with params %s", url, params)
        req = Request('POST',url,headers={'X-Custom':'Test'},data=params)
        prepared = req.prepare()

        logger.info(prepared.headers)
        logger.info(prepared.body)

        try:
            resp = s.send(prepared)
            s.close()
            return resp
        except requests.ConnectionError as ce:
            logger.error("Unable to open with native function. Error: "  + str(ce))

        s.close()
        return None
        
    def prepared_request_morphological(self, input):
        s = Session()

        url = self.render_url('las/analyze')
        params = {'text': input, 'locale':'fi', "forms":"V+N+Nom+Sg"}
        req = Request('POST',url,headers={'X-Custom':'Test'},data=params)
        prepared = req.prepare()

        logger.info(prepared.headers)
        logger.info(prepared.body)

        try:
            resp = s.send(prepared)
            s.close()
            return resp
        except requests.ConnectionError as ce:
            logger.error("Unable to open with native function. Error: "  + str(ce))

        s.close()
        return None
    
    def pretty_print_POST(self,req):
        """
        At this point it is completely built and ready
        to be fired; it is "prepared".
    
        However pay attention at the formatting used in 
        this function because it is programmed to be pretty 
        printed and may differ from the actual request.
        """
        logger.debug('{}\n{}\n{}\n\n{}'.format(
            '-----------START-----------',
            req.method + ' ' + req.url,
            '\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
            req.body,
        ))

    def render_url(self, addition):
        url = ""
        if self.base_url[len(self.base_url) - 1] != "/":
            url = self.base_url + "/" + addition
        else:
            url = self.base_url + addition
        return url

