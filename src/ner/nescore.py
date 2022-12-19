import logging, logging.config

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('ne')

class NeScore:
    def __init__(self):
        self.longest = 0 # longest entity is the best entity
        self.ne_type = 0 # importance of types of entities
        self.method = 0 # reliability of the method used for extraction of entity from text
        self.link = 0 # has been linked to some ontology
        self.ne_simple_type = 0 # there is a upper level simplificated type and it's score
        self.ne_priority = {"PersonName": 9, "PlaceName": 6, "OrganizationName": 7, "ExpressionTime": 8,
                            "AddressName": 10, "PoliticalLocation": 5, "GeographicalLocation": 4,
                            "EducationalOrganization": 6, "VocationName":5, "AnonymEntity": 1,
                            "CorporationName":7, "SportsOrganizations":8,
                            "CultureOrganization":8, "PoliticalOrganization":8,
                            "MediaOrganization":8, "Title":5, "FinancialOrganization":8,
                            "Executive":7, "Event":6, "LocationStructure":3, "AstronomicalLocation":4,
                            "AnimalPerson":9, "MythicalPerson":8, "Product":9, "ClockTime":8,
                            "UnitNumeric":9, "CurrencyNumeric":6, "Other":1, "DomainKnowledge":3,
                            "SocialSecurityNumber":10, "CarLicensePlate":10,
                            "IPAddress":10, "UrlAddress":10, "EmailAddress":10, "PhoneNumber":10, "RegistryDiaryNumber":10, "CourtDecision":10, "Statutes":10, "Law":9,
                            "Works":7
                            }
        self.ne_simple_types = {"PersonName": "PersonName", "PlaceName": "PlaceName", "OrganizationName": "OrganizationName", "ExpressionTime": "ExpressionTime",
                            "AddressName": "PlaceName", "PoliticalLocation": "PlaceName", "GeographicalLocation": "PlaceName",
                            "EducationalOrganization": "OrganizationName", "VocationName": "VocationName", "AnonymEntity": "AnonymEntity",
                            "CorporationName": "OrganizationName", "SportsOrganizations": "OrganizationName",
                            "CultureOrganization": "OrganizationName", "PoliticalOrganization": "OrganizationName",
                            "MediaOrganization": "OrganizationName", "Title": "VocationName", "FinancialOrganization": "OrganizationName",
                            "Executive": "OrganizationName", "Event": "Event", "LocationStructure": "PlaceName", "AstronomicalLocation": "PlaceName",
                            "AnimalPerson": "PersonName", "MythicalPerson": "PersonName", "Product": "Product", "ClockTime": "ExpressionTime",
                            "UnitNumeric": "UnitNumeric", "CurrencyNumeric": "UnitNumeric", "Other": "AnonymEntity", "DomainKnowledge": "DomainKnowledge",
                            "SocialSecurityNumber": "SocialSecurityNumber", "CarLicensePlate": "CarLicensePlate",
                            "IPAddress": "IPAddress", "UrlAddress": "UrlAddress", "EmailAddress": "EmailAddress", "PhoneNumber": "PhoneNumber",
                            "RegistryDiaryNumber": "RegistryDiaryNumber", "CourtDecision": "Law", "Statutes": "Law", "Law":"Law",
                                "Works":"Works"
                            }

    def add_simple_type_score(self, type):
        simple_type = self.get_ne_simple_type(type)
        if simple_type != None:
            self.ne_simple_type = self.ne_priority[simple_type]
        else:
            self.ne_simple_type = 0

    def get_ne_simple_type(self, type):
        if type in self.ne_simple_types:
            return self.ne_simple_types[type]
        return None

    def total_score_simplified(self, type):
        simple = self.ne_simple_types[type]
        simple_score = self.ne_priority[simple]
        s = self.longest + self.link + self.method + simple_score
        return int(s)

    def total_score(self):
        s = self.longest + self.link + self.method + self.ne_type + self.ne_simple_type
        return int(s)

    def set_longest(self, score):
        self.longest = score

    def set_ne_type(self, score):
        self.ne_type = score

    def set_link(self, score):
        self.link = score

    def set_method(self, score):
        self.method = score

    def get_method(self):
        return self.method

    def get_types(self):
        return self.ne_priority.keys()

    def set_type_score(self, type):
        self.ne_type = self.ne_priority[type]

    def __repr__(self):
        return str(self.total_score()) + " = " + str(self.longest) + " (longest) + " + str(self.ne_type) + " (type) + " + str(self.ne_simple_type) + " (simple type) + " + str(self.method) + " (methods) + " + str(self.link) + " (linkage)"

    def __str__(self):
        return str(self.total_score()) + " = " + str(self.longest) + " (longest) + " + str(self.ne_type) + " (type) + " + str(self.ne_simple_type) + " (simple type) + " + str(self.method) + " (methods) + " + str(self.link) + " (linkage)"

