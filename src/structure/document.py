from src.structure.sentence import Sentence
from src.structure.word import Word
from src.ner.namedentity import NamedEntity
from src.structure.structure import Structure
from src.structure.paragraph import Paragraph
from src.structure.title import Title
import logging.config
import nltk
import nltk.data
import urllib
import xml.etree.ElementTree as ET
from datetime import datetime as dt
import csv
from lxml.etree import XMLParser,HTMLParser
import re

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
from collections import OrderedDict

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('doc')

class Document:
    def __init__(self):
        self.structure = None
        self.sid = 1
        self.full_document = None
        self.text = ""
        self.morphological_analysis = dict()

    # parse dictionary containing xml tags and values
    def parse(self, input, paragraph=None,pid=0,prev_paragraph=None, title=None,tid=0,prev_title=None, prev_structure=None, html_level=0):

        if pid == 0:
            pid = 1  # paragraph id

        if tid == 0:
            tid = 1

        self.text = input

        # sentence for paragraph
        sentence = Sentence()
        if paragraph == None:
            paragraph = Paragraph(id=pid, sentences=None)
        if prev_title == None:
            title = None
        if self.structure == None:
            self.structure = Structure()

        if self.type_list_or_tuple(input):
            for item in input:
                for k1, v1 in item.items():
                    if k1 == "h2" or k1 == "h3" or k1 == "h4" or k1 == "h1":
                        prev_title, tid, title, prev_structure = self.parse_title(k1, prev_title, tid, title, v1, prev_structure)
                    elif k1 == "div":
                        paragraph, pid, prev_paragraph, title, tid, prev_title, prev_structure=self.parse(v1, paragraph, pid, prev_paragraph, title, tid, prev_title)
                    elif k1 == "p":
                        paragraph, pid, prev_paragraph, prev_structure = self.parse_paragraph(paragraph, pid, prev_paragraph, v1, prev_structure)
        else:
            logger.warn('Error: Input is not a iterable list but a %s', type(input))
            for k1, v1 in input.items():
                if k1 == "h2" or k1 == "h3" or k1 == "h4" or k1 == "h1":
                    prev_title, tid, title, prev_structure = self.parse_title(k1, prev_title, tid, title, v1,
                                                                              prev_structure)
                elif k1 == "div":
                    paragraph, pid, prev_paragraph, title, tid, prev_title, prev_structure=self.parse(v1, paragraph, pid, prev_paragraph, title, tid, prev_title)
                elif k1 == "p":
                    paragraph, pid, prev_paragraph, prev_structure = self.parse_paragraph(paragraph, pid,
                                                                                          prev_paragraph, v1,
                                                                                          prev_structure)
        return paragraph,pid,prev_paragraph, title,tid,prev_title, prev_structure

    def parse_paragraph(self, paragraph, pid, prev_paragraph, v1, prev_structure, xpath=None):
        self.sentence_parsing(v1, paragraph)
        paragraph.set_p_element(xpath)
        self.structure.set_paragraph(pid, paragraph)
        self.structure.add_structure(self.sid, paragraph)

        # updating pid, initate new paragraph
        self.sid += 1
        pid = pid + 1
        prev_paragraph = paragraph
        prev_structure = paragraph

        paragraph = Paragraph(id=pid, sentences=None, xpath=None)
        return paragraph, pid, prev_paragraph, prev_structure

    def parse_title(self, k1, prev_title, tid, title, v1, prev_structure):
        if title == None:
            title = Title(id=tid, sentences=None, level=k1)
        strtitle = self.extraxt_title(k1, v1)
        self.title_sentence_parsing(strtitle, title)
        self.structure.set_title(tid, title)
        self.structure.add_structure(self.sid, title)
        title.set_level(k1)

        tid += 1
        self.sid += 1
        prev_structure = title
        prev_title = title
        title = Title(id=tid, sentences=None, level=None)
        return prev_title, tid, title, prev_structure

    def type_list_or_tuple(self, x):
        if type(x) is list:
            return True
        elif type(x) is tuple:
            return False
        else:
            return False

    def sentence_parsing(self, val, paragraph):
        sentence = Sentence()
        sentence.set_paragraph(paragraph)
        paragraph_start_char = paragraph.get_start_char_location()

        prev_sentence = None
        for v in val:
            sentences = self.tokenization(v)

            sid = 1
            for s in sentences:
                sentence_start_char = paragraph_start_char + v.find(s)
                sentence_end_char = sentence_start_char + len(s)
                logger.info("[DOC] sentence-parsing: %s, %s",self.full_document[sentence_start_char:sentence_end_char],s)
                if self.full_document[sentence_start_char:sentence_end_char] != s:
                    logger.error("[ERROR] %s", v.find(s))
                    logger.error("[ERROR] %s, %s-%s", s, sentence_start_char, "-", sentence_end_char)
                    logger.error("[ERROR] %s -> %s -> %s", s, self.full_document[sentence_start_char:sentence_end_char], self.full_document)

                words = self.words_to_dict(s)
                sentence.set_sentence(sid, None, prev_sentence, words, "", s)
                sentence.set_start_char_location(sentence_start_char)
                sentence.set_end_char_location(sentence_end_char)
                paragraph.add_sentence(sid, sentence)
                paragraph.set_paragraph_string(v)

                prev_sentence = sentence
                sentence = Sentence()
                sentence.set_paragraph(paragraph)
                sid += 1

    def check_indentation(self):
        pass

    def title_sentence_parsing(self, v, title):
        sentence = Sentence()
        prev_sentence = None

        sentences = self.tokenization(v)
        sid = 1
        for s in sentences:
            words = self.words_to_dict(s)
            sentence.set_sentence(sid, None, prev_sentence, words, "", s)
            title.add_sentence(sid, sentence)
            title.set_title_string(v)

            prev_sentence = sentence
            sentence = Sentence()
            sid += 1

    def extraxt_title(self, level, title):
        if type(title) == str:
            return title
        else:
            for tpl, val in title.items():
                if tpl == '#text':
                    return val

    # tokenizing text to a list of tokens (words, punctuation, etc.)
    def word_tokenizator(self, sent):
        added = self.compile_pattern()

        pattern = r'''(?x)          # set flag to allow verbose regexps
                (?:[A-ZÖÄÅa-zöäå]\.)+(?=\s)         # abbreviations(both upper and lower case, like "e.g.", "U.S.A.")
                | (?:[0-9]+)(?=[.!?]\s+[A-ZÖÄÅ])         # order numbers at end of a sentence
                | (?:[0-9]+\.)+(?=[ )])         # order numbers "14. ", "(47.)"
                | (?:ao|eaa|eKr|em|eo|esim|huom|jaa|jKr|jms|jne|ks|l|ma|ml|mm|mrd|n|nk|no|ns|o.s|oto|puh|so|tjsp|tm|tms|tmv|ts|v|va|vrt|vs|vt|ym|yms|yo|V|RN:o|p|fp|ipu|kp|kok|lib|liik|ps|peruss|sin|pp|tl|ske|kesk|kd|r|sd|vas|vihr|ktp|komm|ref)\.  # abbreviations
                | [/({\['"”».](?=\S)  # opening bracket/quotes
                | (?:\S+)(?=[.,;:?!(){}\[\]'"»”–-][.,;:?!(){}\[\]'"»”–-][.]) # case three punctuation marks: '... quoted!'.
                | (?:\S+)(?=[.,;:?!(){}\[\]'"»”–-][.,;:?!(){}\[\]'"»”–-]) # case two punctuation marks: ... (something).
                | \S+(?=[.,;:?!(){}\[\]'"»”]+(?:\s|[.]|$)) # word with punctuation at end
                | \w+(?=/\w+) # case: naimisissa/naimaton/leski ...
                | \S+
            '''
        pattern = pattern.replace('$abbr', added)
        return nltk.regexp_tokenize(sent, pattern)

    # compile pattern for abbreviations to be added into the word tokenization
    def compile_pattern(self):
        pattern = '(?:$abbr)\.'
        with open('language-resources/abbreviations.csv') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=';')
            pattern = pattern.replace('$abbr', "|".join(['{0}'.format(x[0]) for x in csv_reader]))
        if '$abbr' in pattern:
            pattern = '(?:ao|eaa|em|eo|huom|jaa|jKr|jms|jne|ks|ma|ml|mrd|nk|no|ns|oto|puh|so|tjsp|tm|tms|tmv|ts|va|vrt|vs|vt|yo|mm|esim|ym|yms|eKr|tjms)\.'
        return pattern

    def words_to_dict(self, string):
        words = OrderedDict()
        word_lst = self.word_tokenizator(string)
        for i in range(0, len(word_lst)):
            words[i] = Word(word_lst[i], None, None, None, i, None)
        return words

    # Tokenization from finnish text to sentences, returns list of sentences
    def tokenization(self, text):
        if text != None:
            tokenizer = self.setup_tokenizer()
            return tokenizer.tokenize(text)

        logger.info("Cannot tokenize NONE")
        return ""

    def setup_tokenizer(self):
        tokenizer = nltk.data.load('tokenizers/punkt/finnish.pickle')
        with open('language-resources/abbreviations.csv') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=';')
            for row in csv_reader:
                tokenizer._params.abbrev_types.add(row[0])
        for i in range(0,301):
            tokenizer._params.abbrev_types.add(str(i))
        return tokenizer

    def parse_text(self, input, paragraph=None,pid=0,prev_paragraph=None, title=None,tid=0,prev_title=None, prev_structure=None):
        texts = input.splitlines()
        self.full_document = input
        logger.debug("Texts: %s",texts)
        self.text=input
        if pid == 0:
            pid = 1  # paragraph id

        if paragraph == None:
            paragraph = Paragraph(id=pid, sentences=None)
        if self.structure == None:
            self.structure = Structure()

        for text in texts:
            if len(text) > 0:
                start = input.find(text)
                end = start + len(text)
                logger.info("[TESTING PARAGRAPH LOCATION] %s, %s, %s - %s", input[start:end], text, start, end)
                if input[start:end] != text:
                    logger.error("[ERROR] Entity not found from text: %s, %s", input[start:end], text)
                paragraph.set_start_char_location(start)
                paragraph.set_end_char_location(end)
                paragraph, pid, prev_paragraph, prev_structure = self.parse_paragraph(paragraph, pid,
                                                                                          prev_paragraph, [text],
                                                                                          prev_structure, None)

                logger.info("PARSE TEXT: add paragraph %s (%s)", pid, text)

    def parse_html(self, input, paragraph=None,pid=0,prev_paragraph=None, title=None,tid=0,prev_title=None, prev_structure=None, html_level=0):
        self.full_document = input
        input, declaration = self.extract_declarations(input)
        magical_parser = HTMLParser(encoding='utf-8', recover=True, remove_comments=True)
        tree = ET.parse(StringIO(input), magical_parser)  # or pass in an open file object
        ignore_tags = ["style", "script", "head", "title", "header","head" ,"footer", "ul", "html", "ol", "span", "a",
                       "table", "select", "th", "option", "input", "iframe", "img", "meta", "tr", "menu", "link"]

        if pid == 0:
            pid = 1  # paragraph id
        # sentence for paragraph
        sentence = Sentence()
        if paragraph == None:
            paragraph = Paragraph(id=pid, sentences=None)
        if self.structure == None:
            self.structure = Structure()
            self.structure.set_structure_element(tree)

        debugtags=list()
        for elt in tree.iter():
            xpath = str('//%s[contains(text(),"%s")]' % (elt.tag, elt.text))
            if elt.tag not in ignore_tags and elt.text != None:
                logger.debug("[DOC] parse html %s",elt.text)
                start = input.find(elt.text)
                end = start + len(elt.text)
                logger.info("[TESTING PARAGRAPH LOCATION] %s, %s, %s - %s", input[start:end], elt.text, start, end)
                if input[start:end] != elt.text:
                    logger.error("[ERROR] Entity not found from text: %s, %s", input[start:end], elt.text)
                paragraph.set_start_char_location(start)
                paragraph.set_end_char_location(end)
                paragraph.set_paragraph_string(elt.text)
                debugtags.append(elt.tag)
                paragraph, pid, prev_paragraph, prev_structure = self.parse_paragraph(paragraph, pid,
                                                                                  prev_paragraph, [elt.text],
                                                                                  prev_structure, elt)
                self.text += '\n' + elt.text
        logger.info("All accepted tags with content: %s", debugtags)

        return declaration

    def parse_xml(self, input, paragraph=None,pid=0,prev_paragraph=None, title=None,tid=0,prev_title=None, prev_structure=None, html_level=0):
        self.full_document = input
        input, declaration = self.extract_declarations(input)
        magical_parser = XMLParser(encoding='utf-8', recover=True, remove_comments=True)
        tree = ET.parse(StringIO(input), magical_parser)  # or pass in an open file object
        ignore_tags = ["style", "script", "head", "title"]

        if pid == 0:
            pid = 1  # paragraph id
        # sentence for paragraph
        sentence = Sentence()
        if paragraph == None:
            paragraph = Paragraph(id=pid, sentences=None)
        if self.structure == None:
            self.structure = Structure()
            self.structure.set_structure_element(tree)

        debugtags = list()
        for elt in tree.iter():
            xpath = str('//%s[contains(text(),"%s")]' % (elt.tag, elt.text))
            if elt.tag not in ignore_tags and elt.text != None:
                start = input.find(elt.text)
                end = start + len(elt.text)
                logger.info("[TESTING PARAGRAPH LOCATION] %s, %s, %s - %s", input[start:end], elt.text, start, end)
                if input[start:end] != elt.text:
                    logger.error("[ERROR] Entity not found from text: %s, %s", input[start:end], elt.text)
                paragraph.set_start_char_location(start)
                paragraph.set_end_char_location(end)
                debugtags.append(elt.tag)
                debugtags.append(elt.tag)
                paragraph, pid, prev_paragraph, prev_structure = self.parse_paragraph(paragraph, pid,
                                                                                  prev_paragraph, [elt.text],
                                                                                  prev_structure, elt)
                self.text += '\n' + elt.text
        logger.info("All accepted tags with content: %s", debugtags)

        return declaration

    def extract_declarations(self, input):
        regexes = [r'<!DOCTYPE[^>[]*(\[[^]]*\])?>',r'<!doctype[^>[]*(\[[^]]*\])?>']
        results = None
        for reg in regexes:
            res = re.search(reg, input)
            if res != None:
                input = re.sub(reg, '', input)
                results = res.group(0)

        return input, results

    def parse_rdf(self, input):
        words = dict()
        word, upos, feat, edge, id, prev_id, sId, s_uri = "", "", "", "", "", "", 1, 1
        ne_uri, type_uri, begin, end, string = None, "", "", "", ""
        prev_structure, structure_id = "", ""
        ne = None
        pid = 1
        start = 0

        # sentence for paragraph
        sentence = Sentence()
        paragraph = Paragraph()
        structure = Structure()

        if len(input["results"]["bindings"]) > 0:
            for result in input["results"]["bindings"]:
                prev_id = int(sId)
                prev_par = int(pid)
                prev_structure = structure_id
                sId = float(result["y"]["value"])
                pid = int(result["z"]["value"])
                structure_id = result["structure"]["value"]

                if structure_id != prev_structure and start > 0:
                    self.structures.append(structure)
                    structure = Structure()
                    structure.set_structure(structure_id, None)

                if start == 0:
                    structure.set_structure(structure_id, None)
                    paragraph.set_paragraph(pid, None)
                    start = 1

                if (int(sId) != int(prev_id) or pid != prev_par) and s_uri != 1:
                    # change sentence
                    sentence.set_sentence(prev_id, sId, None, words, s_uri)
                    paragraph.add_sentence(prev_id,sentence)
                    sentence = Sentence()
                    words = dict()

                if pid != prev_par:
                    structure.set_paragraph(prev_par, paragraph)
                    paragraph = Paragraph(id=pid, sentences=None)

                w_uri = result["s"]["value"]
                s_uri = result["sentence"]["value"]

                id = int(result["x"]["value"])
                if 'word' in result:
                    w = result["word"]["value"]
                else:
                    w = ""
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
                if 'ne' in result:
                    ne_uri = result["ne"]["value"]
                    type_uri = result["type"]["value"]
                    begin = result["begin"]["value"]
                    end = result["end"]["value"]
                    string = result["string"]["value"]


                if ne_uri is not None:
                    ne = NamedEntity()
                    ne.set_ne(ne_uri, string, begin, end, type_uri)

                # create word and add to the list
                word = Word(w, upos, feat, edge, id, w_uri)
                words[id] = word

            sentence.set_sentence(sId, None, prev_id, words, s_uri)
            paragraph.add_sentence(sId,sentence)
            structure.set_paragraph(pid, paragraph)
            self.structures.append(structure)
        else:
            return False

        return True

    def get_full_text_document(self):
        return self.full_document

    def get_structure(self):
        return self.structure

    def get_sentences(self):
        for struct in self.structure:
            struct.get_sentences()

    def print_nes(self):
        self.structure.print_nes()

    def print_headers(self):
        for id, title in self.structure.get_titles().items():
            title.print_sentences()

    def render_doc_html(self,declaration=None, return_uniques=True, setup=None):
        # get results in HTML format
        # Render json list of entities
        json_list = self.structure.get_named_entities_json_list(return_uniques=return_uniques, setup=setup)

        # render json output
        results = dict()
        results["entities"] = json_list
        results['text'] = self.text
        if setup['content'] == 1:
            # Render annotated text
            html = self.structure.render_html(id=0, setup=setup).replace('&lt;', '<').replace('&gt;', '>')
            if declaration:
                html = declaration + html
            results["content"] = html.replace("&lt;/span&gt;", "</span>").replace("&lt;span", "<span").replace("&gt;", ">").replace("&lt;", "<").replace("&lt;/a>", "</a>").replace("&lt;/div>", "</div>").replace("&lt;a", "<a")

        if setup['get_morphological_analysis'] == 1:
            results['morphological_analysis'] = self.get_morphological_analysis_results()

        # wrapping final output
        data = {'status': 200, 'data': results, 'service':"Tagger, version 1.1.1-beta", 'date':dt.today().strftime('%Y-%m-%d')}
        return data

    def render_xml(self,declaration=None, return_uniques=True, setup=None):
        # get results in XML format
        # Render json list of entities
        json_list = self.structure.get_named_entities_json_list(return_uniques=return_uniques, setup=setup)

        # render json output
        results = dict()
        results["entities"] = json_list
        if setup['content'] == 1:
            # Render annotated text
            html = urllib.parse.unquote(str(self.structure.render_xml(id=0, setup=setup), 'utf-8'))
            if declaration != None:
                html = declaration + html
            logger.info('result %s', html)
            results["content"] = html.replace("&lt;/span&gt;", "</span>").replace("&lt;span", "<span").replace("&gt;", ">").replace("&lt;", "<").replace("&lt;/a>", "</a>").replace("&lt;/div>", "</div>").replace("&lt;a", "<a")

        if setup['get_morphological_analysis'] == 1:
            results['morphological_analysis'] = self.get_morphological_analysis_results()

        # wrapping final output
        data = {'status': 200, 'data': results, 'service':"Tagger, version 1.1.1-beta", 'date':dt.today().strftime('%Y-%m-%d')}
        return data

    def render_doc_xml(self, return_uniques=True, setup=None):
        # get results in XML format

        # Render json list of entities
        json_list = self.structure.get_named_entities_json_list(return_uniques=return_uniques, setup=setup)

        # render json output
        results = dict()
        results["entities"] = json_list

        if setup['content'] == 1:
            # Render annotated text
            html = self.structure.render_html_xml(id=0, setup=setup).replace('&lt;', '<').replace('&gt;', '>')
            logger.info('result %s', html)
            results["content"] = str(html)

        if setup['get_morphological_analysis'] == 1:
            results['morphological_analysis'] = self.get_morphological_analysis_results()

        # wrapping final output
        data = {'status': 200, 'data': results, 'service':"Tagger, version 1.1.1-beta", 'date':dt.today().strftime('%Y-%m-%d')}
        return data

    def render_doc_text(self, return_uniques=True, setup=None):
        # get results in text format
        json_list = self.structure.get_named_entities_json_list(return_uniques=return_uniques, setup=setup)

        # render json output
        results = dict()
        results["entities"] = json_list

        if setup['content'] == 1:
            # Render annotated text
            html = self.structure.render_text(id=0, setup=setup)
            logger.info('result %s', html)
            results["content"] = str(html)

        if setup['get_morphological_analysis'] == 1:
            results['morphological_analysis'] = self.get_morphological_analysis_results()

        # wrapping final output
        data = {'status': 200, 'data': results, 'service':"Tagger, version 1.1.1-beta", 'date':dt.today().strftime('%Y-%m-%d')}

        return data

    def set_morphological_analysis_results(self, results, method):
        self.morphological_analysis[method] = results

    def get_morphological_analysis_results(self):
        return self.morphological_analysis

    def get_morphological_analysis_results_methods(self):
        return self.morphological_analysis.keys()

    def get_morphological_analysis_results_for_method(self, method):
        if method in self.morphological_analysis.keys():
            return self.morphological_analysis[method]
        logger.warning("No such method used for morphological analysis, %s", str(method))

    def __str__(self):
        return str(self.structure)