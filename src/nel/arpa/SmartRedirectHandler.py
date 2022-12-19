import urllib.request as req

class SmartRedirectHandler(req.HTTPRedirectHandler):    
    def http_error_301(self, req, fp, code, msg, headers):  
        result = req.HTTPRedirectHandler.http_error_301(
            self, req, fp, code, msg, headers)              
        result.status = code                                
        return result                                       

    def http_error_302(self, req, fp, code, msg, headers):  
        result = req.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers)              
        result.status = code                                
        return result                                       

