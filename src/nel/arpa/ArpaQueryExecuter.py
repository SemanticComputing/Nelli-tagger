import sys
import urllib.request as req
import urllib.parse as parse
import urllib.error as err
import gzip
#import httplib2
#import httplib2
import requests
import logging, time
from urllib.request import HTTPHandler as HTTPHandler
from io import StringIO
from src.nel.arpa.SmartRedirectHandler import SmartRedirectHandler
from src.nel.arpa.DefaultErrorHandler import DefaultErrorHandler

USER_AGENT = 'OpenAnything/1.0 +http://diveintopython.org/http_web_services/'

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('arpa')

class ArpaQueryExecuter(object):
    def __init__(self, agent, source, querystring):
        self.__agent = agent
        self.__source = source
        self.__querystring = querystring
        
    def get_agent(self):
        return self.__agent


    def get_source(self):
        return self.__source


    def get_querystring(self):
        return self.__querystring


    def set_agent(self, value):
        self.__agent = value


    def set_source(self, value):
        self.__source = value


    def set_querystring(self, value):
        self.__querystring = value


    def del_agent(self):
        del self.__agent


    def del_source(self):
        del self.__source


    def del_querystring(self):
        del self.__querystring       
    

    def executeQuery(self, source, data, etag=None, lastmodified=None, agent=USER_AGENT):
        '''URL, filename, or string --> stream
    
        This function lets you define parsers that take any input source
        (URL, pathname to local or network file, or actual data as a string)
        and deal with it in a uniform manner.  Returned object is guaranteed
        to have all the basic stdio read methods (read, readline, readlines).
        Just .close() the object when you're done with it.
    
        If the etag argument is supplied, it will be used as the value of an
        If-None-Match request header.
    
        If the lastmodified argument is supplied, it must be a formatted
        date/time string in GMT (as returned in the Last-Modified header of
        a previous request).  The formatted date/time will be used
        as the value of an If-Modified-Since request header.
    
        If the agent argument is supplied, it will be used as the value of a
        User-Agent request header.
        '''
        request = None
        try:

            if source == '-':
                logger.warning("Query not executed, sys")
                return sys.stdin

            if parse.urlparse(source)[0] == 'http' or parse.urlparse(source)[0] == 'https':

                header = { 'User-Agent': agent,
                            'Accept-encoding': 'utf-8'}

                if etag:
                    header.update('If-None-Match', etag)
                if lastmodified:
                    header.update('If-Modified-Since', lastmodified)

                request = requests.get(source, params=data, headers=header)

                # Basic error handling
                sleep_time=30
                while request.status_code != 200 and sleep_time < 31:# 4000:
                    request = requests.get(source, params=data, headers=header)

                    # check. Substitute with appropriate HTTP code.
                    if request.status_code == 200:
                        return request
                    else:
                        logger.warning("Unexpected error: %s ", request.status_code)
                        logger.warning("For request data: %s", data)
                        logger.warning("For request url: %s", request.url)
                        logger.warning("For request req: %s", request)
                        logger.debug("Unable to reach ARPA and waiting for " + str(sleep_time)+"s")
                        time.sleep(sleep_time)
                        sleep_time=sleep_time*2
                        # handle the error case. connection.read() will still contain data
                        # if any was returned, but it probably won't be of any use
        
        # try to open with native open function (if source is a filename)

            return request
        except Exception as e:
            logger.debug("Unable to connect. Error: " + str(request) + " Detail: " + str(e))
    
        # treat source as string
        return StringIO(str(request).replace(":","|")+"|"+str(source)+"|"+str(data))
    

    def formSuccessfulResultJson(self, result, f):
        resultdata = f
        try:
            result['data'] = resultdata.decode("utf-8")
        except AttributeError:
            result['data'] = resultdata

        try:
            if hasattr(f, 'headers'):
                # save ETag, if the server sent one
                result['etag'] = f.headers.get('ETag') # save Last-Modified header, if the server sent one
                result['lastmodified'] = f.headers.get('Last-Modified')
                result['encoding'] = f.headers.get('content-encoding')
            if hasattr(f, 'url'):
                result['url'] = f.url
                result['status'] = 200
            if hasattr(f, 'status_code'):
                result['status'] = f.status_code
        except Exception as e:
            logger.warning("Unexpected error: %s ", f.status_code)
            logger.warning("For request url: %s", f.url)
            logger.warning("For request req: %s", f)
            logger.error(e)


    def formErrorResultJson(self, result, f):
        res = f
        arr = res.split('|')
        result['result'] = "Error"
        if len(arr) == 4:
            result['code'] = arr[0].strip()
            result['value'] = arr[1].strip()
            result['url'] = arr[2].strip()
            result['params'] = arr[3].strip()
        else:
            result['returned'] = res

    def fetch(self, source, data, etag=None, last_modified=None, agent=USER_AGENT):  
        '''Fetch data and metadata from a URL, file, stream, or string'''
        result = {}                                                      
        f = self.executeQuery(source, data, etag, last_modified, agent)
        if not(isinstance(f, StringIO)):
            self.formSuccessfulResultJson(result, f)
        else:
            self.formErrorResultJson(result, f)
        
        return f
    
    def getArpa(self):
        url = self.__source
        f = {'text' : self.__querystring}
        return self.fetch(url, f)
