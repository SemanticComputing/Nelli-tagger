from src.structure.word import Word

from src.structure.sentence import Sentence
import logging.config

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('doc')

class Paragraph:
    def __init__(self, id=0, sentences=None, xpath=None, start_char=None, end_char=None):
        if sentences is None:
            self.sentences = dict()
        else:
            self.sentences = sentences
        self.id = int(id)
        self.string = ""
        self.html_level = 0
        self.p_element = xpath
        self.annotated_text = ""

        self.start_char_location = None
        self.set_start_char_location(start_char)

        self.end_char_location = None
        self.set_end_char_location(end_char)

    def set_start_char_location(self, start):
        if start is not None:
            self.start_char_location = start

    def set_end_char_location(self, end):
        if end is not None:
            self.end_char_location = end

    def get_start_char_location(self):
        return self.start_char_location

    def get_end_char_location(self):
        return self.end_char_location

    def set_p_element(self, p):
        self.p_element = p

    def get_p_element(self):
        return self.p_element

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

    def get_paragraph_string(self):
        return self.string

    def get_html_identifier(self):
        return "p"+self.id

    def set_paragraph_string(self, s):
        self.string = s

    def set_paragraph(self, id, sentences):
        if sentences is None:
            self.sentences = dict()
        else:
            self.sentences = sentences
        self.id = id

    def print_nes(self):
        for s in self.sentences:
            nes = s.get_nes()
            for ne in nes:
                logger.info(ne)

    def add_sentence(self, id, sentence):
        sid = int(float(id))
        if sid not in self.sentences.keys():
            self.sentences[sid]=sentence

    def render_text(self, idx, setup=None):
        anno_paragraph = ""
        for id, sentence in self.sentences.items():
            s, idx = sentence.get_annotated_sentence(idx, setup=setup)
            if len(anno_paragraph) == 0:
                anno_paragraph += s
            else:
                anno_paragraph += " " + s
        if len(self.annotated_text) == 0:
            self.annotated_text = anno_paragraph
        else:
            logger.warn("Element none for %s %s" % (anno_paragraph, self.id))
        return anno_paragraph, idx

    def render_html(self, idx, setup=None):
        logger.info('[HTML] RENDER PARAGRAPH %s', str(self.id))
        anno_paragraph = ""
        for id, sentence in self.sentences.items():
            s, idx = sentence.get_annotated_sentence(idx, setup=setup)
            if len(anno_paragraph) == 0:
                anno_paragraph += s
            else:
                anno_paragraph += " " + s
        if self.p_element is not None:
            self.p_element.text = anno_paragraph
            logger.info("Changed text %s", anno_paragraph)
        else:
            logger.warn("None?",self.p_element)
            logger.warn("Element none for %s %s" % (anno_paragraph, self.id))
        return anno_paragraph, idx

    def render_xml(self, idx, setup=None):
        logger.info('[XML] RENDER PARAGRAPH %s', str(self.id))
        anno_paragraph = ""
        for id, sentence in self.sentences.items():
            s, idx = sentence.get_annotated_sentence(idx, setup=setup)
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
        return "Paragraph "+str(self.id) + " (" + str(len(self.sentences)) + " sentences)"
