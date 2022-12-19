import urllib.request as req
import urllib.error as err

class DefaultErrorHandler(req.HTTPDefaultErrorHandler):   
    def http_error_default(self, req, fp, code, msg, headers):
        result = err.HTTPError(                           
            req.get_full_url(), code, msg, headers, fp)       
        result.status = code
        return result   