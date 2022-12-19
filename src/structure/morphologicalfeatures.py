class MorphologicalFeatures:
    def __init__(self):
        self.case = ""
        self.number = ""
        self.mood = ""
        self.tense = ""
        self.person = ""
        self.voice = ""
        self.verbform = ""
        self.degree = ""
        self.partform = ""
        self.edge = ""
        self.adptype = ""
        self.numtype = ""
        self.derivation = ""
        self.prontype = ""

        self.unknown = True

    def get_case(self):
        return self.case

    def get_edge(self):
        return self.edge

    def set_case(self, case):
        self.case = case

    def get_number(self):
        return self.number

    def set_number(self, num):
        self.number = num

    def get_mood(self):
        return self.mood

    def get_tense(self):
        return self.tense

    def get_person(self):
        return self.person

    def get_verbform(self):
        return self.verbform

    def get_degree(self):
        return self.degree

    def get_partform(self):
        return self.partform

    def get_derivation(self):
        return self.derivation

    def get_prontype(self):
        return self.prontype

    def get_adptype(self):
        return self.adptype

    def get_numtype(self):
        return self.numtype

    def parse(self, features):
        if features == None:
            return

        if "Case" in features:
            self.case = features["Case"]
        if "Number" in features:
            self.number = features["Number"]
        if "Mood" in features:
            self.mood = features["Mood"]
        if "Tense" in features:
            self.tense = features["Tense"]
        if "Person" in features:
            self.person = features["Person"]
        if "VerbForm" in features:
            self.verbform = features["VerbForm"]
        if "Degree" in features:
            self.degree = features["Degree"]
        if "PartForm" in features:
            self.partform = features["PartForm"]
        if "Derivation" in features:
            self.derivation = features["Derivation"]
        if "PronType" in features:
            self.prontype = features["PronType"]
        if "AdpType" in features:
            self.adptype = features["AdpType"]
        if "NumType" in features:
            self.numtype = features["NumType"]

    def match(self, c, n):
        if self.case == c and self.number == n:
            return True
        else:
            return False

    def __str__(self):
        s = "Case=" + str(self.case) + "|" + "Number=" + str(self.number)
        return s

    def __eq__(self, other):
        if other is None:
            return False

        if self.case != other.get_case():
            return False

        if self.number != other.get_number():
            return False

        if self.mood != other.get_mood():
            return False

        if self.tense != other.get_tense():
            return False

        if self.person != other.get_person():
            return False

        if self.verbform != other.get_verbform():
            return False

        if self.degree != other.get_degree():
            return False

        if self.partform != other.get_partform():
            return False

        if self.prontype != other.get_prontype():
            return False

        if self.derivation != other.get_derivation():
            return False

        if self.adptype != other.get_adptype():
            return False

        if self.numtype != other.get_numtype():
            return False

        return True
