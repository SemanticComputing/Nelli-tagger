from src.ner.namefinder.run_namefinder import RunNameFinder
from src.ner.namedentity import NamedEntity
import os, collections, re
import logging, logging.config
from nltk.tokenize.treebank import TreebankWordDetokenizer
from src.ner.parse_results import Ner, ParseResults

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('namefinder')


class NerNameFinder(Ner):
    def __init__(self, data, text_data, ne_dictionary=None, context=0):
        tool, pool_size, pool_number, level, lemmatize = super().read_configs('NAMEFINDER')

        if ne_dictionary == None:
            self.ne_dictionary = dict()
        else:
            self.ne_dictionary = ne_dictionary

        self.orig_data = data
        if text_data == None:
            self.input_data = super().create_ner_input_data(data)
        else:
            self.input_data = text_data

        self.tool = tool
        self.pool_size = pool_size
        self.pool_number = pool_number
        self.lemmatize = lemmatize
        self.context = context

    def run_tool(self):
        namefinder = RunNameFinder("", "", self.tool, self.input_data, self.pool_number, self.pool_size)
        namefinder.run(multiprocess=True, context=self.context)
        logger.info("Ending processing")
        return namefinder

    def parse_results(self, namefinder):
        namefinder_parser = ParseNameFinderResults()
        namefinder_parser.parse(self.input_data, namefinder.get_output_files())
        nes = namefinder_parser.get_nes()
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
                text = TreebankWordDetokenizer().detokenize(words).replace(' , ', ', ')
                text = re.sub(r'([A-ZÅÄÖa-zåäö]+)( )(\-|\–)( )([A-ZÅÄÖa-zåäö]+)', r'\1\3\4\5', text)
                data[ind] = re.sub(r'([0-9]+)( )(\.)', r'\1\3', text)
                logger.info("[CREATE INPUT] Tokenization for ind %s is %s", ind, data[ind])
        return data

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
                        except AttributeError as arr:
                            logger.error(traceback.format_exc())
                            logger.error("[AttributeError] Error caused in transforming indeces: %s", dct)
                        except Exception as err:
                            logger.error(traceback.format_exc())
                            logger.error("[Exception] Error caused in transforming indeces %s", dct)
                            logger.error("Retry indentification of indeces...")

                            start = None
                            end = None

                        if start != None and end != None:
                            logger.info('Add for sentence %s (%s:%s)', sentence.get_sentence_string(), start, end)

                            # add char locations
                            for i, j in enumerate(start):

                                logger.info("Iterate: %s %s", i, start)
                                begin = start[i]
                                stop = end[i]
                                end_word = sentence.get_word(stop)
                                start_word = sentence.get_word(begin)
                                name = str(structu_id) + "_" + str(parid) + "_" + str(senid) + "_" + str(
                                    begin) + "_" + str(stop)
                                logger.info("start %s", str(start_word))
                                logger.info("end %s", str(end_word))
                                if (start_word.get_upos() == "NOUN" or start_word.get_upos() == "PROPN"):
                                    self.create_named_entity(begin, stop, sentence, nes[ne].get_type(), "name-finder",
                                                             1, nes[ne].get_lemma(),
                                                             start, start_word, end, end_word, related=None,
                                                             linked=None, titles=nes[ne].get_titles(),
                                                             gender=nes[ne].get_gender(), date=nes[ne].get_dates())

                        else:
                            logger.warn("[NAME-FINDER] Could not find ne: ", str(nes[ne]),
                                        nes[ne].get_string().strip().replace(".", " ."))
                            logger.warning("[NAME-FINDER] Could not find ne %s %s", str(nes[ne]),
                                           nes[ne].get_string().strip().replace(".", " ."))
                            logger.warning("[NAME-FINDER] For sentence %s", str(sentence.get_words()))

                        sentence.lemmatize_nes()
                    else:
                        logger.warn('Unidentifiable struct', str(struct))

        # add new keys to dict
        for n in new_nes.keys():
            if n in nes.keys():
                logger.debug("Update key %s for NE %s != %s", str(n), str(new_nes[n]), str(nes[n]))
            nes[n] = new_nes[n]

        return nes

    def update_ne(self, begin, stop, nne, sentence):

        end_word = sentence.get_word(stop)
        start_word = sentence.get_word(begin)

        logger.debug('start word %s (%s/%s)', start_word.get_word(), start_word.get_start_index(), begin)
        logger.debug('end word %s (%s/%s)', end_word.get_word(), end_word.get_end_index(), stop)

        # error happens here

        if len(nne.get_end_char_index()) > 0:
            if abs(nne.get_end_ind() - stop) < 4:
                nne.set_end_char_index(end_word.get_end_index())
            else:
                logger.warn("Cannot setting word end index %s != %s", str(nne.get_end_ind()), str(stop))
                logger.warn("Problem setting end index %s != %s for %s", str(nne.get_end_char_index()),
                            str(end_word.get_end_index()), str(nne))
        else:
            nne.set_end_char_index(end_word.get_end_index())
            logger.debug("Check if matches: %s", str(abs(nne.get_end_char_index()[0] - end_word.get_end_index())))

        if len(nne.get_start_char_index()) > 0:
            if abs(nne.get_start_ind() - begin) < 4:
                nne.set_start_char_index(start_word.get_start_index())
            else:
                logger.warn("Cannot setting word end index %s != %s", str(nne.get_start_ind()), str(begin))
                logger.warn("Problem setting start index %s != %s for %s", str(nne.get_start_char_index()),
                            str(start_word.get_start_index()), str(nne))
        else:
            nne.set_start_char_index(start_word.get_start_index())
            logger.debug("Check if matches: %s", str(abs(nne.get_start_char_index()[0] - start_word.get_start_index())))

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

    def create_named_entity(self, ind, pattern_end, sentence, ne_type, method, score, lemma, start, start_word, end,
                            end_word, related=None, linked=None, titles=None, gender=None, date=None):

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
            logger.info("[NAME-FINDER] New NE can be added")

            self.set_ne(ind, lemma, method, ne, ne_type, pattern_end, sentence, string, titles=titles, gender=gender,
                        date=date)
        else:
            # If there exists already same or similar entity...
            if ne.get_type() != ne_type:
                logger.info("[NAME-FINDER] OLD NE , but the type is different and still related to each other")
                # ... but the type is different and still related to each other (e.g. PlaceName vs. GeographicalLocation)
                nes = ne
                nes.set_method(method, score)
                nes.set_simple_type_score()
                ne = NamedEntity()
                self.set_ne(ind, lemma, method, ne, ne_type, pattern_end, sentence, string, titles=titles,
                            gender=gender, date=date)
                ne.set_simple_type_score()
            elif ne.get_string() != string and ne.get_type() == ne_type:
                logger.info("[NAME-FINDER] OLD NE , but the string label is different and the type is the same")
                # ... but the string label is different and the type is the same (e.g. Sauli Väinämö Niinistö and Väinämä Niinistö)
                nes = ne
                nes.set_method(method, score)
                nes.set_simple_type_score()
                ne = NamedEntity()
                self.set_ne(ind, lemma, method, ne, ne_type, pattern_end, sentence, string, titles=titles,
                            gender=gender, date=date)
                ne.set_simple_type_score()
            else:
                logger.info("[NAME-FINDER] OLD NE , but it is the same entity, just update the existing")
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
                if titles:
                    ne.set_titles(titles)
                if gender:
                    ne.set_gender(gender)
                if date:
                    ne.set_date(date)
                logger.info('start word %s %s %s', start_word.get_word(), start_word.get_start_index(), ind)
                logger.info('end word %s %s %s', end_word.get_word(), end_word.get_end_index(), pattern_end - 1)

        if linked != None:
            ne.add_related_match(lemma, linked)
        ne.set_method(method, score)
        if related != None:
            ne.set_related(related)

        # Add sentence
        sentence.add_ne(ne)

        return ne

    def set_ne(self, ind, lemma, method, ne, ne_type, pattern_end, sentence, string, titles=None, gender=None,
               date=None):
        if ind == pattern_end:
            ne.set_ne("", string, ind, pattern_end, ne_type, method, titles=titles, gender=gender, date=date)
            end_word = sentence.get_word(pattern_end)
            start_word = sentence.get_word(ind)
            ne.set_related_words(sentence.list_words_between_indeces(ind, pattern_end))
            logger.info('start word %s %s %s', start_word.get_word(), start_word.get_start_index(), ind)
            logger.info('end word %s %s %s', end_word.get_word(), end_word.get_end_index(), pattern_end)
            ne.set_end_char_index(end_word.get_end_index())
            ne.set_start_char_index(start_word.get_start_index())
            ne.set_document_end_char_index(
                sentence.get_document_start_char_location() + start_word.get_start_index() + len(string))
            ne.set_document_start_char_index(sentence.get_document_start_char_location() + start_word.get_start_index())
            ne.set_case(end_word.get_case())
            ne.set_lemma(lemma)
        else:
            ne.set_ne("", string, ind, pattern_end, ne_type, method, titles=titles, gender=gender, date=date)
            end_word = sentence.get_word(pattern_end)
            start_word = sentence.get_word(ind)
            ne.set_related_words(sentence.list_words_between_indeces(ind, pattern_end))
            logger.info('start word %s %s %s', start_word.get_word(), start_word.get_start_index(), ind)
            logger.info('end word %s %s %s', end_word.get_word(), end_word.get_end_index(), pattern_end)
            ne.set_end_char_index(end_word.get_end_index())
            ne.set_start_char_index(start_word.get_start_index())
            ne.set_document_end_char_index(
                sentence.get_document_start_char_location() + start_word.get_start_index() + len(string))
            ne.set_document_start_char_index(sentence.get_document_start_char_location() + start_word.get_start_index())
            ne.set_case(end_word.get_case())
            ne.set_lemma(lemma)

    def __repr__(self):
        return "NerNameFinder"

    def __str__(self):
        return "NerNameFinder"


class ParseNameFinderResults(ParseResults):
    def __init__(self):
        self.nes = dict()
        self.ne_type_labels = {"PersonName": "PersonName"}

    def parse(self, data, results):
        for k, v in results.items():
            if k in data:
                logger.info('found correct sentence %s (%s): %s', data[k], k, v)
                gender = ""
                title = ""
                dates = ""
                for name in v['entities']:
                    item = k
                    key = name['full_name']
                    value = name['names']
                    logger.debug('Item %s', item)
                    logger.debug('Value %s', value)
                    words = data[k].split(" ")
                    logger.debug('start to parse: %s', name)
                    startA = min([int(res['start_ind']) for res in value])
                    endA = max([int(res['end_ind']) for res in value])

                    tag = "PersonName"
                    entity = name['full_name'].strip()
                    lemma = name['full_name_lemma'].strip()
                    if 'gender' in name.keys():
                        gender = name['gender'].strip()
                    if 'titles' in name.keys():
                        print(name['titles'])
                        title = list(name['titles'])
                    if 'date' in name.keys():
                        dates = name['lifespan_time'].strip()
                    string = entity.split(" ")

                    # reality check, find the real indeces from the sentence
                    both = set(words).intersection(string)
                    indices_A = [words.index(x) for x in both]
                    logger.info("[NAME-FINDER] Check location: %s:%s (both=%s, indeces_A=%s)", startA, endA, both,
                                indices_A)
                    if len(indices_A) == 0:
                        logger.debug("String %s", string)
                        logger.debug("Words %s", words)
                        logger.debug("Both %s", both)
                        start = startA
                        end = endA
                    else:
                        start = indices_A[0]
                        end = indices_A[-1]

                    if (start - end) != (endA - startA):
                        if len(indices_A) > 0:
                            start = indices_A[0]
                            end = indices_A[-1]
                        else:
                            start = startA
                            end = endA

                    loc_name = str(k) + '_' + str(start) + '_' + str(end)
                    if tag in self.ne_type_labels.keys():
                        self.add_ne(start, end, loc_name, self.ne_type_labels[tag], entity, id, lemma=lemma,
                                    gender=gender, titles=title, dates=dates)
                    else:
                        logger.info("[NAME-FINDER] Unable to add ne %s (%s-%s, %s, %s)", entity, start, end, loc_name,
                                    self.ne_type_labels[tag])

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

    def add_ne(self, first_ind, last_ind, name, tag, value, id=0, lemma="", titles="", gender="", dates=""):
        ne = NamedEntity()
        ne.set_ne("", value, first_ind, last_ind, tag, "name-finder", None, id, lemma=lemma, titles=titles,
                  gender=gender, date=dates)
        self.nes[name] = ne

    def get_nes(self):
        return self.nes
