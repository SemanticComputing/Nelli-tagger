from abc import ABC, abstractmethod
import collections, re
from nltk.tokenize.treebank import TreebankWordDetokenizer
import nltk, csv
import configparser
from configparser import Error, ParsingError, MissingSectionHeaderError, NoOptionError, DuplicateOptionError, DuplicateSectionError, NoSectionError
from flask import abort
import os, sys, traceback
from distutils.util import strtobool
import logging, logging.config

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('base')

class Ner(ABC):

    @abstractmethod
    def run_tool(self):
        pass

    def create_ner_input_data(self, doc, level=2):
        # levels: 1 = full document (only for full text documents), 2 = paragraph, 3 = sentence
        data = collections.OrderedDict()
        document = doc.get_full_text_document()

        if level == 1 and document != None:
            data[str(0)] = document

        elif level == 2 or (level == 1 and document == None):
            # if user wants to execute a document by paragraph OR the application is unable to use full document
            structure = doc.get_structure()

            for structu_id, parval in structure.get_structures().items():
                parid = parval.get_id()
                for sid, sentence in parval.get_sentences().items():
                    ind = str(structu_id) + "_" + str(parid) + "_" + str(sid)
                    words = [word.get_word() for word in list(sentence.get_words().values())]
                    text = TreebankWordDetokenizer().detokenize(words).replace(' , ', ', ').replace(' . ', '. ')
                    text = re.sub(r'([A-ZÅÄÖa-zåäö]+)( )(\-|\–)( )([A-ZÅÄÖa-zåäö]+)', r'\1\3\4\5', text)
                    data[ind] = re.sub(r'([0-9]+)( )(\.)', r'\1\3', text)
                    logger.info("[CREATE INPUT] %s: %s",ind, text)

        return data

    @abstractmethod
    def write_nes(self, nes):
        pass

    def read_configs(self, env):
        tool = ""
        pool_number = 4
        pool_size = 4
        level = 3
        lemmatize = False

        try:
            config = configparser.ConfigParser()
            config.read('confs/services.ini')

            if env in config:
                tool = config[env]['url']
                pool_number = int(config[env]['pool_number'])
                pool_size = int(config[env]['pool_size'])
                level = int(self.translate_level(str(config[env]['input_feed_level'])))
                lemmatize = strtobool(config[env]['lemmatize'])
            else:
                err_msg = 'The environment is not set: %s' % (env)
                raise Exception(err_msg)
        except Error as e:
            logger.error("[ERROR] ConfigParser error: %s", sys.exc_info()[0])
            traceback.print_exc()
            abort(500)
        except Exception as err:
            logger.error("[ERROR] Unexpected error: %s", sys.exc_info()[0])
            traceback.print_exc()
            abort(500)

        return tool, pool_size, pool_number, level, lemmatize

    def translate_level(self, level):
        # levels: 1 = full document (only for full text documents), 2 = paragraph, 3 = sentence
        if level == "fulltext":
            return 1
        elif level == "paragraph":
            return 2
        elif level == "sentence":
            return 3
        else:
            logger.warning("Unable to determine level: %s", level)
            return 1


class ParseResults(ABC):

    @abstractmethod
    def parse(self, data, results):
        pass

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



