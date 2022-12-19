from src.structure.word import Word
from src.structure.sentence import Sentence
import logging

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('doc')

class Title:
    def __init__(self, id=0, sentences=None, level=None):
        if sentences is None:
            self.sentences = dict()
        else:
            self.sentences = sentences
        self.id = int(id)
        if level is not None:
            self.level = level
        else:
            self.level = "h1"
        self.string = ""
        self.html_level = 0
        logger.debug('Adding title, %s', str(self))
    def parse(self, input):
        words = dict()
        word, upos, feat, edge, id, prev_id, sId, s_uri = "", "", "", "", "", "", 1, 1

        # sentence for paragraph
        sentence = Sentence()
        for result in input["results"]["bindings"]:
            prev_id = int(sId)
            sId = float(result["y"]["value"])

            if sId != prev_id:
                # change sentence
                sentence.set_sentence(prev_id, sId, None, words, s_uri)
                self.sentences.append(sentence)
                sentence = Sentence()
                words = dict()

            s_uri = result["s"]["value"]
            w = result["word"]["value"]
            id = int(result["x"]["value"])
            if 'upos' in result:
                upos = result["upos"]["value"]
            else:
                upos = "UNKNOWN"
            if 'feat' in result:
                feat = result["feat"]["value"]
            else:
                feat = "UNKNOWN"
            if 'edge' in result:
                edge = result["edge"]["value"]
            else:
                edge = "UNKNOWN"

            # create word and add to the list
            word = Word(w, upos, feat, edge, id, s_uri)
            words[id] = word

    def get_sentences(self):
        return self.sentences

    def get_sentence(self, sid):
        id = int(float(sid))
        return self.sentences.get(id)

    def get_id(self):
        return self.id

    def get_level(self):
        return self.level

    def get_html_identifier(self):
        return "t"+self.id

    def get_title_string(self):
        logger.debug('get string: %s', self.string)
        return self.string

    def set_level(self, level):
        self.level = level

    def set_title_string(self, s):
        self.string = s

    def set_title(self, id, sentences):
        if sentences is None:
            self.sentences = dict()
        else:
            self.sentences = sentences
        self.id = id

    def print_nes(self):
        for s in self.sentences:
            nes = s.get_nes()
            for ne in nes:
                logging.info(ne)

    def print_sentences(self):
        for id, s in self.get_sentences().items():
            logger.debug("%s %s",id, s)

    def add_sentence(self, id, sentence):
        sid = int(float(id))
        if sid not in self.sentences.keys():
            self.sentences[sid]=sentence

    def render_html(self, parent, idx):
        logger.debug('RENDER TITLE, %s', self.id)
        anno_paragraph = ""
        for id, sentence in self.sentences.items():
            s,idx = sentence.get_annotated_sentence(parent, idx)
            if len(anno_paragraph) == 0:
                anno_paragraph += s
            else:
                anno_paragraph += " " + s

        return anno_paragraph, idx

    def __repr__(self):
        s = ""
        for sentence in self.sentences:
            s = s + str(sentence)
        return str(len(self.sentences))

    def __str__(self):
        return "Title " +str(self.id)+" (" + str(len(self.sentences)) + " sentences, "+"LEVEL:"+self.get_level()+")"