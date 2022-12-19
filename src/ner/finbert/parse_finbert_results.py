from src.ner.finbert.run_finbert import RunFinBert
from src.ner.namedentity import NamedEntity
import re
import logging, logging.config
from src.ner.parse_results import Ner, ParseResults
import numpy as np
from numpy.lib.stride_tricks import as_strided
import traceback

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('finbert')


class NerFinBert(Ner):
    def __init__(self, data, text_data, ne_dictionary=None):
        tool, pool_size, pool_number, level, lemmatize = super().read_configs('FINBERT')
        if ne_dictionary is None:
            self.ne_dictionary = dict()
        else:
            self.ne_dictionary = ne_dictionary

        self.orig_data = data
        if text_data is None:
            self.input_data = super().create_ner_input_data(data, level=level)
        else:
            self.input_data = text_data  # self.create_ner_input_data(data)
        self.document_level_data = super().create_ner_input_data(data, level=2)

        self.tool = tool
        self.pool_size = pool_size
        self.pool_number = pool_number
        self.lemmatize = lemmatize

    def run_tool(self):
        finbert = RunFinBert("", "", self.tool, self.input_data, self.pool_number, self.pool_size)
        finbert.run(multiprocess=True)
        logger.info("Ending processing")
        return finbert

    def parse_results(self, finbert):
        finBertParser = ParseFinBertResults()
        finBertParser.parse(self.input_data, finbert.get_output_files(), self.document_level_data)
        nes = finBertParser.get_nes()
        self.write_nes(nes)
        return True

    def write_nes(self, nes):
        import traceback

        STRUCT_ID = 0
        PAR_ID = 1
        SEN_ID = 2
        necounter = 0
        start = 3
        end = 4
        new_nes = dict()

        logger.info('WRITE NES --- %s', nes.keys())
        for ne in nes.keys():
            split = ne.split("_")
            structid = split[STRUCT_ID]
            parid = split[PAR_ID]
            senid = split[SEN_ID]
            string = nes[ne].get_string()

            if string in self.ne_dictionary:
                nes[ne].set_id(self.ne_dictionary[string])
            else:
                nes[ne].set_id(necounter)
                necounter += 1
                self.ne_dictionary[string] = necounter

            structures = self.orig_data.get_structure().get_structures()
            for structu_id, struct in structures.items():
                logger.debug("STRUCT (i.e. which paragraph): %s==%s? (%s)", structid, structu_id, struct)
                if int(structu_id) == int(structid):

                    if struct != None:

                        sentence = struct.get_sentence(senid)
                        dct = sentence.find_word_ind(nes[ne].get_string().strip().split())
                        try:
                            start = list(dct.keys())
                            end = list(dct.values())
                            if start == None and end == None:
                                dct = sentence.find_word_ind(list(reversed(nes[ne].get_string().strip().split())))
                                start = list(dct.keys())
                                end = list(dct.values())

                            if start == None and end == None:
                                dct = sentence.find_word_ind(nes[ne].get_string().strip().replace(".", " .").split())
                                start = list(dct.keys())
                                end = list(dct.values())
                        except Exception as err:
                            logger.error(traceback.format_exc())
                            logger.error("Error caused in transforming indeces", dct)
                            logger.error("Retry indentification of indeces...")

                            start = None
                            end = None

                        if start != None and end != None:
                            logger.info('Add for sentence %s (%s:%s), %s', sentence.get_sentence_string(), start, end,
                                        nes[ne].get_string())
                            logger.info('That has words %s', sentence.get_words())

                            # add char locations
                            for i, j in enumerate(start):
                                logger.info("%s %s", i, start)
                                begin = start[i]
                                stop = end[i]
                                name = str(structu_id) + "_" + str(parid) + "_" + str(senid) + "_" + str(
                                    begin) + "_" + str(stop)
                                end_word = sentence.get_word(stop)
                                start_word = sentence.get_word(begin)
                                self.create_named_entity(begin, stop, sentence, nes[ne].get_type(), "finbert", 1,
                                                         nes[ne].get_lemma(),
                                                         start, start_word, end, end_word, nes[ne].get_string(),
                                                         related=None, linked=None)

                        else:
                            logger.warn("Could not find ne: %s, %s ", str(nes[ne]),
                                        nes[ne].get_string().strip().replace(".", " ."))
                            logger.warning("Could not find ne %s %s", str(nes[ne]),
                                           nes[ne].get_string().strip().replace(".", " ."))
                            logger.warning("For sentence %s", str(sentence.get_words()))
                        sentence.lemmatize_nes()
                    else:
                        logger.warn('Unidentifiable struct', str(struct))

        # add new keys to dict
        for n in new_nes.keys():
            if n in nes.keys():
                logger.debug("Update key %s for NE %s != %s", str(n), str(new_nes[n]), str(nes[n]))
            nes[n] = new_nes[n]

        return nes

    def create_named_entity(self, ind, pattern_end, sentence, ne_type, method, score, lemma, start, start_word, end,
                            end_word, label, related=None, linked=None):

        end = int(pattern_end)
        string = ""

        real_ne, words = sentence.get_named_entity_string(ind, end)
        if re.sub(' +', ' ', real_ne) != re.sub(' +', ' ', label):
            msg = "The label %s doesn't match the extracted string label %s" % (label, real_ne)
            logger.error(msg)
            if sentence.get_sentence_string()[words[0].get_start_index():words[-1].get_end_index()] != label:
                string = label
            else:
                string = sentence.get_sentence_string()[words[0].get_start_index():words[-1].get_end_index()]
        else:
            string = real_ne

        logger.info("[FINBERT] Found string %s (%s) for indeces %s-%s (%s-%s)", string, real_ne, ind, end,
                    words[0].get_start_index(), words[0].get_end_index())

        # add checkup for existing similar entity at same location
        ne = sentence.get_similar_named_entities_at(ind, pattern_end, string, ne_type)

        if ne == None:
            # Add completely new named entity
            ne = NamedEntity()
            logger.debug("[FINBERT] New NE can be added")

            self.set_ne(ind, lemma, method, ne, ne_type, pattern_end, sentence, string)
        else:
            # If there exists already same or similar entity...
            if ne.get_type() != ne_type:
                logger.debug("[FINBERT] OLD NE , but the type is different and still related to each other")
                # ... but the type is different and still related to each other (e.g. PlaceName vs. GeographicalLocation)
                nes = ne
                nes.set_method(method, score)
                nes.set_simple_type_score()
                ne = NamedEntity()
                self.set_ne(ind, lemma, method, ne, ne_type, pattern_end, sentence, string)
                ne.set_simple_type_score()
            elif ne.get_string() != string and ne.get_type() == ne_type:
                logger.debug("[FINBERT] OLD NE , but the string label is different and the type is the same")
                # ... but the string label is different and the type is the same (e.g. Sauli Väinämö Niinistö and Väinämä Niinistö)
                nes = ne
                nes.set_method(method, score)
                nes.set_simple_type_score()
                ne = NamedEntity()
                self.set_ne(ind, lemma, method, ne, ne_type, pattern_end, sentence, string)
                ne.set_simple_type_score()
            else:
                logger.debug("[FINBERT] OLD NE , but it is the same entity, just update the existing")
                # ... but it is the same entity, just update the existing
                end_word = sentence.get_word(pattern_end)
                start_word = sentence.get_word(ind)
                if len(ne.get_related_words()) < 1:
                    ne.set_related_words(sentence.list_words_between_indeces(ind, pattern_end))
                if ne.get_end_char_index() == 0:
                    ne.set_end_char_index(end_word.get_end_index())
                    ne.set_document_end_char_index(
                        sentence.get_document_end_char_location() + end_word.get_end_index())
                if ne.get_start_char_index() == 0:
                    ne.set_start_char_index(start_word.get_start_index())
                    ne.set_document_start_char_index(
                        sentence.get_document_start_char_location() + start_word.get_start_index())
                ne.set_case(end_word.get_case())
                ne.set_lemma(lemma)
                logger.debug('[FINBERT] start word %s %s %s %s', start_word.get_word(), start_word.get_start_index(),
                             ind, ne.get_document_start_char_index())
                logger.debug('end word %s %s %s %s', end_word.get_word(), end_word.get_end_index(), pattern_end - 1,
                             ne.get_document_end_char_index())

        if linked != None:
            ne.add_related_match(lemma, linked)
        ne.set_method(method, score)
        if related != None:
            ne.set_related(related)

        # Add sentence
        sentence.add_ne(ne)

        return ne

    def set_ne(self, ind, lemma, method, ne, ne_type, pattern_end, sentence, string):
        if ind == pattern_end:
            self.update_named_entity(ind, lemma, method, ne, ne_type, pattern_end, sentence, string)
        else:
            self.update_named_entity(ind, lemma, method, ne, ne_type, pattern_end, sentence, string)

    def update_named_entity(self, ind, lemma, method, ne, ne_type, pattern_end, sentence, string):
        ne.set_ne("", string, ind, pattern_end, ne_type, method)
        end_word = sentence.get_word(pattern_end)
        start_word = sentence.get_word(ind)
        ne.set_related_words(sentence.list_words_between_indeces(ind, pattern_end))
        logger.info('[FINBERT] start word %s %s %s', start_word.get_word(), start_word.get_start_index(), ind)
        logger.info('[FINBERT] end word %s %s %s', end_word.get_word(), end_word.get_end_index(), pattern_end)
        ne.set_end_char_index(end_word.get_end_index())
        ne.set_start_char_index(start_word.get_start_index())
        ne.set_document_end_char_index(
            sentence.get_document_start_char_location() + start_word.get_start_index() + len(string))
        ne.set_document_start_char_index(sentence.get_document_start_char_location() + start_word.get_start_index())
        logger.info("[FINBERT] setting global index for %s: %s-%s from %s (%s) to %s (%s) %s", string,
                    ne.get_document_start_char_index(), ne.get_document_end_char_index(), start_word,
                    start_word.get_start_index(), end_word, end_word.get_end_index(), len(string))
        ne.set_case(end_word.get_case())
        ne.set_lemma(lemma)

    def get_data(self):
        return self.orig_data

    def get_ne_dictionary(self):
        return self.ne_dictionary

    def __repr__(self):
        return "NerFinBert"

    def __str__(self):
        return "NerFinBert"


class ParseFinBertResults(ParseResults):
    def __init__(self):
        self.nes = dict()
        self.ne_type_labels = {"ORG": "OrganizationName",
                               "PERSON": "PersonName", "PER": "PersonName",
                               "DATE": "ExpressionTime", "TIME": "ExpressionTime",
                               "GPE": "PoliticalLocation",
                               "LOC": "GeographicalLocation",
                               "PRO": "Product", "PRODUCT": "Product",
                               "FAC": "LocationStructure", "EVENT": "Event", "MONEY": "CurrencyNumeric",
                               "PERCENT": "UnitNumeric", "QUANTITY": "UnitNumeric", "LAW": "Law",
                               "WORK_OF_ART": "Works"}

        # 'PERSON': 'Proper names of people',
        # 'NORP': 'Nationalities, religious and political affiliations',
        # 'FAC': 'Facilities: man-made structures',
        # 'ORG': 'Organizations: companies, government agencies, educational institutions, sport teams, etc.',
        # 'GPE': 'Geopolitical entities: countries, cities, states, provinces, municipalities, etc.',
        # 'LOC': 'Geographical locations other than geopolitial entities',
        # 'PRODUCT': 'Products including devices, vehicles, software and services',
        # 'DATE': 'Dates and periods of a day or longer',
        # 'TIME': 'Times of day and durations shorter than a day',
        # 'PERCENT': 'Percentages',
        # 'MONEY': 'Monetary values',
        # 'QUANTITY': 'Measurements with standardized units',
        # 'ORDINAL': 'Ordinal numbers (first, second, etc.)',
        # 'CARDINAL': 'Cardinal numbers (one, two, etc.)',
        # 'EVENT': 'Named hurricanes, battles, wars, sports events, attacks, etc.',
        # 'WORK_OF_ART': 'Books, songs, television programs, etc., including awards',
        # 'LAW': 'Laws, treaties, and other named legal documents',
        # 'LANGUAGE': 'Named languages',

    def oldparse(self, data, results):
        for k, v in results.items():
            if k in data:
                logger.info('found correct sentence %s (%s): %s', data[k], k, v)
                item = k
                value = v
                logger.debug('Item %s', item)
                logger.debug('Value %s', value)
                for res in value:
                    words = super().word_tokenizator(data[k])
                    logger.debug('start to parse: %s', res)
                    startA = int(res['word_start_index'])
                    endA = int(res['word_end_index'])

                    tag = res['type']
                    entity = res['entity'].strip()
                    string = entity.split(" ")

                    # reality check, find the real indeces from the sentence
                    both = set(words).intersection(string)
                    indices_A = [words.index(x) for x in both]
                    if len(indices_A) == 0:
                        logger.debug("String %s", string)
                        logger.debug("Words %s", words)
                        logger.debug("Both %s", both)
                        start = startA
                        end = endA
                    else:
                        start = indices_A[0]
                        end = indices_A[-1]

                    if (start - end) != (startA - endA):
                        start = start
                        end = start + startA - endA

                    name = str(k) + '_' + str(start) + '_' + str(end)

                    self.add_ne(start, end, name, tag, entity)

    def parse(self, data, results, document_level_data):
        for chunk, entitylist in results.items():
            # go through array of entities and create each entity
            for e in entitylist:
                entity_type = self.decode_entity_type(e['type'])
                # find position of an entity in text
                for sentence in self.find_location_in_text(document_level_data, e['text']):
                    start_points = self.find_word_location_in_sentence(
                        super().word_tokenizator(document_level_data[sentence]), super().word_tokenizator(e['text']))
                    for start in start_points:
                        end = start + len(super().word_tokenizator(e['text'])) - 1
                        name = str(sentence) + '_' + str(start) + '_' + str(end)
                        self.add_ne(start, end, name, entity_type, e['text'])

    def find_word_location_in_sentence(self, words, entity):
        # https://stackoverflow.com/questions/14890216/return-the-indexes-of-a-sub-array-in-an-array
        subarr = np.array(entity)
        arr = np.array(words)

        a = len(arr)
        b = len(subarr)
        a_view = None
        try:
            a_view = as_strided(arr, shape=(a - b + 1, b),
                                strides=(arr.dtype.itemsize,) * 2)
            return np.where(np.all(a_view == subarr, axis=1))[0]
        except ValueError as verr:
            logger.warning("Unable to find words (%s) in sentence (%s): %s", words, entity, verr)
            logger.error(traceback.format_exc())
        except Exception as err:
            logger.warning("Unable to find words (%s) in sentence (%s): %s", words, entity, err)
            logger.error(traceback.format_exc())

        return list()

    def find_location_in_text(self, data, entity):
        for k, v in data.items():
            if entity in data[k]:
                yield k

    def decode_entity_type(self, type):
        if type in self.ne_type_labels:
            return self.ne_type_labels[type]
        else:
            logger.warning("Unidentified type %s: Replacing it with other for the time being. TODO: fix mapping.", type)
            return "Other"

    def add_ne(self, first_ind, last_ind, name, tag, value, start_char_ind=None, end_char_ind=None):
        ne = NamedEntity()
        ne.set_ne("", value, first_ind, last_ind, tag, "finbert", start_char_ind=start_char_ind,
                  end_char_ind=end_char_ind)
        self.nes[name] = ne

    def get_nes(self):
        return self.nes
