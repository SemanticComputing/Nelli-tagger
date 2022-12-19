from src.structure.morphologicalfeatures import MorphologicalFeatures
import logging, logging.config

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('doc')

class Word:
    def __init__(self, word, upos, feat, edge, id, w_uri):
        self.uri = w_uri
        self.word = word
        self.upos = upos
        self.lemma = ""
        self.xpos = ""
        self.deprel = ""
        self.misc = ""
        self.deps = ""
        self.head = ""
        self.edge = edge
        self.feat = MorphologicalFeatures()
        self.start_index = 0
        self.end_index = 0
        if feat is not None:
            self.set_feat(feat)
        self.id = int(id)

    def set_upos(self, upos):
        self.upos = upos

    def get_lemma(self):
        return self.lemma.replace('#','')

    def get_lemma_with_compound_separator(self):
        return self.lemma

    def set_lemma(self, lemma):
        if self.word[0].isupper() == True and lemma[0].isupper() == False:
            self.lemma = lemma.capitalize()
        else:
            self.lemma = lemma

    def get_xpos(self):
        return self.xpos

    def set_xpos(self, xpos):
        self.xpos = xpos

    def get_deprel(self):
        return self.deprel

    def set_deprel(self, deprel):
        self.deprel = deprel

    def get_misc(self):
        return self.misc

    def set_misc(self, misc):
        self.misc = misc

    def get_deps(self):
        return self.deps

    def set_deps(self, deps):
        self.deps = deps

    def get_head(self):
        return self.head

    def set_head(self, head):
        self.head = head

    def get_uri(self):
        return self.uri

    def get_word(self):
        return self.word

    def get_upos(self):
        return self.upos

    def get_feat(self):
        return self.feat

    def get_id(self):
        return self.id

    def get_start_index(self):
        return self.start_index

    def get_end_index(self):
        return self.end_index

    def set_start_index(self, ind):
        self.start_index = ind

    def set_end_index(self, ind):
        self.end_index = ind

    def set_feat(self, feat):
        self.feat = feat

    def get_edge(self):
        return self.edge

    def set_edge(self, edge):
        self.edge = edge

    def get_case(self):
        return self.feat.get_case()

    def get_number(self):
        return self.feat.get_number()

    def word_type_match(self, u, c, n):
        if self.upos == u:
            if self.feat.match(c, n):
                return True
        return False

    def is_first_letter_uppercase(self):
        letter = self.get_word()[:1]
        return letter.isupper()

    def __repr__(self):
        return str(self.word)

    def __str__(self):
        s = "Word instance "+str(self.id) + ": " + self.word + ", " + str(self.upos)
        return s

    def __hash__(self):
        return hash((self.word))

    def __eq__(self, other):
        if other is None:
            return False

        if self.uri != other.get_uri():
            return False

        if self.word != other.get_word():
            return False

        if self.id != other.get_id():
            return False

        if self.upos != other.get_upos():
            return False

        return True
