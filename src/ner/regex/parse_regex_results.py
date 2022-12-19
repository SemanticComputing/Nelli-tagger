from src.ner.regex.run_regex import RunRegex
from src.ner.namedentity import NamedEntity
import os, collections, re
import logging, logging.config
from nltk.tokenize.treebank import TreebankWordDetokenizer
from src.ner.parse_results import Ner, ParseResults

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('regex')

class NerRegex(Ner):
    def __init__(self, data, text_data, ne_dictionary=None):
        tool, pool_size, pool_number, level, lemmatize = super().read_configs('REGEX')
        if ne_dictionary == None:
            self.ne_dictionary = dict()
        else:
            self.ne_dictionary = ne_dictionary

        self.orig_data = data
        if text_data == None:
            self.input_data=super().create_ner_input_data(data)
        else:
            self.input_data = text_data  # self.create_ner_input_data(data)

        self.tool = tool
        self.pool_size = pool_size
        self.pool_number = pool_number
        self.lemmatize = lemmatize

    def run_tool(self):
        regex = RunRegex("", "", self.tool, self.input_data, self.pool_number, self.pool_size)
        regex.run(multiprocess=True)
        logger.info("Ending processing")
        return regex

    def parse_results(self, regex):
        regexParser = ParseRegexResults()
        regexParser.parse(self.input_data,regex.get_output_files())
        nes = regexParser.get_nes()
        self.write_nes(nes)
        return True

    def create_ner_input_data(self, doc):
        data = collections.OrderedDict()
        structure = doc.get_structure()

        for structu_id, parval in structure.get_structures().items():
            parid = parval.get_id()
            for sid, sentence in parval.get_sentences().items():
                ind = str(structu_id) + "_" + str(parid) + "_" + str(sid)
                words = [word.get_word() for word in list(sentence.get_words().values())]
                logger.info("[CREATE INPUT] Words %s for ind %s", words, ind)
                text = TreebankWordDetokenizer().detokenize(words).replace(' - ', '- ').replace(' , ', ', ')
                data[ind] = re.sub(r'([0-9]+)( )(\.)',r'\1\3',text)
                logger.info("[CREATE INPUT] Tokenization for ind %s is %s", ind, data[ind])
        logger.info("[REGEX DATA] %s",data)
        return data

    def write_nes(self, nes):
        import traceback

        STRUCT_ID = 0
        PAR_ID = 1
        SEN_ID = 2
        necounter = 0
        start = 3
        end = 4
        new_nes=dict()

        logger.info('WRITE NES --- %s',nes.keys())
        for ne in nes.keys():
            split = ne.split("_")
            structid = split[STRUCT_ID]
            parid = split[PAR_ID]
            senid = split[SEN_ID]
            string = nes[ne].get_string()
            logger.info('NE --- %s', ne)

            if len(string) > 0:

                if string in self.ne_dictionary:
                    nes[ne].set_id(self.ne_dictionary[string])
                else:
                    nes[ne].set_id(necounter)
                    necounter += 1
                    self.ne_dictionary[string] = necounter

                structures = self.orig_data.get_structure().get_structures()
                for structu_id,struct in structures.items():
                    logger.info("STRUCT: %s-%s %s",structid, structu_id, struct)
                    if int(structu_id) == int(structid):
                        logger.info('MATCH!')

                        if struct != None:
                            sentence = struct.get_sentence(senid)
                            logger.info("[REGEX] sentence, %s", str(sentence))
                            logger.info("[REGEX] string, %s", str(nes[ne].get_string()))
                            dct = sentence.find_word_ind(nes[ne].get_string().strip().split())
                            logger.info("[REGEX] Got indeces %s", dct)
                            try:
                                start = list(dct.keys())
                                end = list(dct.values())
                                if start == None and end == None:
                                    dct = sentence.find_word_ind(list(reversed(nes[ne].get_string().strip().split())))
                                    start = list(dct.keys())
                                    end = list(dct.values())

                                if start == None and end == None:
                                    dct = sentence.find_word_ind(nes[ne].get_string().strip().replace("."," .").split())
                                    start = list(dct.keys())
                                    end = list(dct.values())
                            except Exception as err:
                                logger.error(traceback.format_exc())
                                logger.error("Error caused in transforming indeces",dct)
                                logger.error("Retry indentification of indeces...")

                                start = None
                                end = None

                            if start != None and end != None:
                                logger.info('[REGEX] Add for sentence %s (%s:%s), %s', sentence.get_sentence_string(), start, end, nes[ne].get_string())

                                # add char locations
                                for i,j in enumerate(start):
                                    logger.info("%s %s", i, start)
                                    begin = start[i]
                                    stop = end[i]
                                    name = str(structu_id) + "_" + str(parid) + "_" + str(senid) + "_" + str(
                                        begin) + "_" + str(stop)
                                    end_word = sentence.get_word(stop)
                                    start_word = sentence.get_word(begin)
                                    self.create_named_entity(begin, stop, sentence, nes[ne].get_type(), "regex", 1,
                                                             nes[ne].get_lemma(),
                                                             start, start_word, end, end_word, related=None, linked=nes[ne].get_related_matches())

                            else:
                                logger.warn("Could not find ne: ", str(nes[ne]), nes[ne].get_string().strip().replace(".", " .") )
                                logger.warning("Could not find ne %s %s", str(nes[ne]), nes[ne].get_string().strip().replace(".", " ."))
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

    def create_named_entity(self, ind, pattern_end, sentence, ne_type, method, score, lemma, start, start_word, end, end_word, related=None, linked=None):

        end = int(pattern_end)
        string, words = sentence.get_named_entity_string(ind, end)

        if type(start) != type(end):
            if type(start) == list and type(end) != list:
                end = [end]
            elif type(start) != list and type(end) == list:
                start = [start]
        else:
            start = int(start)
            end = int(end)

        # add checkup for existing similar entity at same location
        ne = sentence.get_similar_named_entities_at(ind, pattern_end, string, ne_type)

        if ne == None:
            # Add completely new named entity
            ne = NamedEntity()
            logger.info("[REGEX] New NE can be added: %s", string)

            self.set_ne(ind, lemma, method, ne, ne_type, pattern_end, sentence, string, linked)
        else:
            # If there exists already same or similar entity...
            if ne.get_type() != ne_type:
                logger.info("[REGEX] OLD NE , but the type is different and still related to each other")
                # ... but the type is different and still related to each other (e.g. PlaceName vs. GeographicalLocation)
                nes = ne
                nes.set_method(method, score)
                nes.set_simple_type_score()
                ne = NamedEntity()
                self.set_ne(ind, lemma, method, ne, ne_type, pattern_end, sentence, string, linked)
                ne.set_simple_type_score()
            elif ne.get_string() != string and ne.get_type() == ne_type:
                logger.info("[REGEX] OLD NE , but the string label is different and the type is the same")
                # ... but the string label is different and the type is the same (e.g. Sauli Väinämö Niinistö and Väinämä Niinistö)
                nes = ne
                nes.set_method(method, score)
                nes.set_simple_type_score()
                ne = NamedEntity()
                self.set_ne(ind, lemma, method, ne, ne_type, pattern_end, sentence, string, linked)
                ne.set_simple_type_score()
            else:
                logger.info("[REGEX] OLD NE , but it is the same entity, just update the existing")
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
                ne.set_related_match(related)
                logger.debug('start word %s %s %s', start_word.get_word(), start_word.get_start_index(), ind)
                logger.debug('end word %s %s %s', end_word.get_word(), end_word.get_end_index(), pattern_end - 1)

        if linked != None:
            ne.add_related_match(lemma, linked)
        ne.set_method(method, score)
        if related != None:
            ne.set_related(related)

        # Add sentence
        sentence.add_ne(ne)

        return ne

    def set_ne(self, ind, lemma, method, ne, ne_type, pattern_end, sentence, string, links=dict()):
        if ind == pattern_end:
            self.update_named_entity(ind, lemma, method, ne, ne_type, pattern_end, sentence, string, links)
        else:
            self.update_named_entity(ind, lemma, method, ne, ne_type, pattern_end, sentence, string, links)

    def update_named_entity(self, ind, lemma, method, ne, ne_type, pattern_end, sentence, string, links):
        ne.set_ne("", string, ind, pattern_end, ne_type, method)
        end_word = sentence.get_word(pattern_end)
        start_word = sentence.get_word(ind)
        ne.set_related_words(sentence.list_words_between_indeces(ind, pattern_end))
        logger.info('start word %s %s %s', start_word.get_word(), start_word.get_start_index(), ind)
        logger.info('end word %s %s %s', end_word.get_word(), end_word.get_end_index(), pattern_end)
        ne.set_end_char_index(end_word.get_end_index())
        ne.set_start_char_index(start_word.get_start_index())
        ne.set_document_end_char_index(sentence.get_document_start_char_location() + start_word.get_start_index() + len(string))
        ne.set_document_start_char_index(sentence.get_document_start_char_location() + start_word.get_start_index())
        logger.info("setting global index: %s-%s from %s (%s) to %s (%s)", ne.get_document_start_char_index(), ne.get_document_end_char_index(), start_word,start_word.get_start_index(), end_word, end_word.get_end_index())
        ne.set_case(end_word.get_case())
        ne.set_lemma(lemma)
        ne.set_related_match(links)

    def update_ne(self, begin, stop, nne, sentence):
        end_word = sentence.get_word(stop)
        start_word = sentence.get_word(begin)

        logger.info('NamedEntity %s', nne)
        logger.info('start word %s (%s/%s)', start_word.get_word(), start_word.get_start_index(), begin)
        logger.info('end word %s (%s/%s)', end_word.get_word(), end_word.get_end_index(), stop)

        # error happens here
        if len(nne.get_end_char_index()) > 0:
            if abs(nne.get_end_ind()-stop) < 4:
                nne.set_end_char_index(end_word.get_end_index())
                nne.set_document_end_char_index(sentence.get_document_start_char_location() + start_word.get_start_index() + len(nne.get_string()))

            else:
                logger.warn("Cannot setting word end index %s != %s", str(nne.get_end_ind()), str(stop))
                logger.warn("Problem setting end index %s != %s for %s", str(nne.get_end_char_index()),
                            str(end_word.get_end_index()), str(nne))
        else:
            nne.set_end_char_index(end_word.get_end_index())
            nne.set_document_end_char_index(sentence.get_document_start_char_location() + start_word.get_start_index() + len(nne.get_string()))

            logger.debug("Check if matches: %s",str(abs(nne.get_end_char_index()[0]-end_word.get_end_index())))

        if len(nne.get_start_char_index()) > 0:
            if abs(nne.get_start_ind()-begin) < 4:
                nne.set_start_char_index(start_word.get_start_index())
                nne.set_document_start_char_index(
                    sentence.get_document_start_char_location() + start_word.get_start_index())
            else:
                logger.warn("Cannot setting word end index %s != %s", str(nne.get_start_ind()), str(begin))
                logger.warn("Problem setting start index %s != %s for %s", str(nne.get_start_char_index()), str(start_word.get_start_index()), str(nne))
        else:
            nne.set_start_char_index(start_word.get_start_index())
            nne.set_document_start_char_index(sentence.get_document_start_char_location() + start_word.get_start_index())
            logger.debug("Check if matches: %s",str(abs(nne.get_start_char_index()[0] - start_word.get_start_index())))

        if nne.get_start_ind() == 0 and nne.get_end_ind() == 0:
            nne.set_start_ind([begin])
            nne.set_end_ind([stop])

        nne.set_related_words(sentence.list_words_between_indeces(begin, stop))

        logger.debug("%s %s(%s %s %s), %s %s", nne.get_string(), ' LEN ', nne.get_start_char_index(), '-',
                     nne.get_end_char_index(), 'vrt. ', len(nne.get_string()))

    def get_data(self):
        return self.orig_data

    def get_ne_dictionary(self):
        return self.ne_dictionary

    def __repr__(self):
        return "NerRegex"

    def __str__(self):
        return "NerRegex"


class ParseRegexResults(ParseResults):
    def __init__(self):
        self.nes = dict()
        self.ne_type_labels = {"SOCIAL_SECURITY": "SocialSecurityNumber", "CAR_LICENSE_PLATE": "CarLicensePlate",
                               "DATETIME": "ExpressionTime", "IP_v4_ADDRESS": "IPAddress",
                               "IP_v6_ADDRESS": "IPAddress", "URL": "UrlAddress",
                               "EMAIL": "EmailAddress", "PHONE_NUMBER": "PhoneNumber", "REGISTRY_DIARY_NUMBER":"RegistryDiaryNumber",
                               "MEASURE_UNIT":"UnitNumeric", "CURRENCY":"CurrencyNumeric", "COURT_DECISION":"CourtDecision", "STATUTES":"Statutes"}

    def parse(self, data, results):
        logger.debug("[REKSI] results: %s", results)
        logger.debug("[REKSI] data: %s", data)
        for k,v in results.items():
            logger.debug("[REKSI] k: %s", k)
            logger.debug("[REKSI] v: %s", v)
            if k in data:
                logger.info('found correct sentence %s (%s): %s', data[k], k, v)
                item = k
                sentence = str(v['sentence'])
                sentence_txt = str(v['text'])
                value = v['entities']
                logger.info('Item %s/%s',item, sentence)
                logger.info('Value %s', value)
                logger.info('[GOT] Item, Value [%s] %s', sentence, sentence_txt)

                for res in value:
                    words = data[k].split(" ")
                    logger.info('[REGEX] start to parse: %s',res)
                    startA = int(res['start_index'])
                    endA = int(res['end_index'])
                    links = str(res['links']).split(',')
                    alternate_id = ""

                    tag = res['category']
                    entity = res['entity'].strip()
                    string = entity.split(" ")
                    if len(entity.strip()) > 0:
                        if 'alternate_id' in res:
                            alternate_id = res['alternate_id']

                        # reality check, find the real indeces from the sentence
                        both = set(words).intersection(string)
                        indices_A = [words.index(x) for x in both]

                        if len(indices_A) == 0:
                            logger.debug("String %s",string)
                            logger.debug("Words %s", words)
                            logger.debug("Both %s", both)
                            start = startA
                            end = endA
                        else:
                            start = min(indices_A)
                            end = max(indices_A)

                        logger.info("[PARSE] entity start and end: %s-%s, %s-%s", startA, endA, start, end)
                        if (end-start) != len(both):
                            if (end-start) > len(both): # when the difference between end and start is too large
                                for i in range(end - len(both),end):
                                    if words[i] == words[start]:
                                        start = i
                            elif (end-start) < len(both): # when start is larger than the end
                                for i in range(start,start+len(both)):
                                    if words[i] == words[end]:
                                        end = i

                        name = str(k) + '_' + str(start) + '_' + str(end)
                        if tag in self.ne_type_labels.keys():
                            logger.info("ADD ne %s = %s", str(name),
                                        links)
                            self.add_ne(start, end, name, self.ne_type_labels[tag], entity, id, links, alt_label=alternate_id)


    # saving each ne into a dict with a key (structure_paragraph_sentence_#word#ids)
    def save_ne(self, ner, file, tag):

        first_ind = list(ner.keys())[0]
        last_ind = list(ner.keys())[-1]
        value = ""
        path, fname = os.path.split(file)
        name = os.path.splitext(fname)[0] + "_"
        for n in ner.keys():
            name += "#" + str(n)
            value += " " + str(ner[n])

        self.add_ne(first_ind, last_ind, name, self.ne_type_labels[tag], value)

    def add_ne(self, first_ind, last_ind, name, tag, value, id=0, links=list(), alt_label=""):
        ne = NamedEntity()
        ne.set_ne("", value, first_ind, last_ind, tag, "regex", None, id, value, links)
        ne.add_alt_label(alt_label)
        self.nes[name] = ne

    def get_nes(self):
        return self.nes

