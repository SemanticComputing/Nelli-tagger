from src.ner.finer.run_finer import RunFiner
from src.ner.namedentity import NamedEntity
import logging, logging.config
from src.ner.parse_results import Ner, ParseResults

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('finer')


class NerFiner(Ner):
    def __init__(self, data, text_data, ne_dictionary=None):
        tool, pool_size, pool_number, level, lemmatize = super().read_configs('FINER')

        if ne_dictionary is None:
            self.ne_dictionary = dict()
        else:
            self.ne_dictionary = ne_dictionary

        self.orig_data = data
        if text_data is None:
            self.input_data = super().create_ner_input_data(data)
        else:
            self.input_data = text_data  # self.create_ner_input_data(data)

        self.tool = tool
        self.pool_size = pool_size
        self.pool_number = pool_number
        self.lemmatize = lemmatize

    def run_tool(self):
        finer = RunFiner("", "", self.tool, self.input_data, self.pool_number, self.pool_size)
        finer.run(multiprocess=True)
        return finer

    def parse_results(self, finer):
        finerParser = ParseFinerResults()
        finerParser.parse(self.input_data, finer.get_output_files())
        nes = finerParser.get_nes()
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
            ne_struct_id = split[STRUCT_ID]
            ne_parag_id = split[PAR_ID]
            ne_sen_id = split[SEN_ID]
            string = nes[ne].get_string()

            if string in self.ne_dictionary:
                nes[ne].set_id(self.ne_dictionary[string])
            else:
                nes[ne].set_id(necounter)
                necounter += 1
                self.ne_dictionary[string] = necounter

            structures = self.orig_data.get_structure().get_structures()
            for struct_id, struct in structures.items():
                if int(struct_id) == int(ne_struct_id):
                    if struct != None:

                        sentence = struct.get_sentence(ne_sen_id)
                        dct = sentence.find_word_ind(nes[ne].get_string().strip().split())
                        logger.info("Got indeces %s", dct)
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

                        if start is not None and end is not None:
                            logger.info('Add for sentence %s (%s:%s), %s', sentence.get_sentence_string(), start, end,
                                        nes[ne].get_string())
                            logger.info('That has words %s', sentence.get_words())

                            # add char locations
                            for i, j in enumerate(start):

                                logger.info("%s %s", i, start)
                                begin = start[i]
                                stop = end[i]
                                name = str(struct_id) + "_" + str(ne_parag_id) + "_" + str(ne_sen_id) + "_" + str(
                                    begin) + "_" + str(stop)
                                if name in nes.keys() and (
                                        begin == nes[ne].get_start_ind() and stop == nes[ne].get_end_ind()):
                                    logger.info("[%s] Name %s in nes.keys()=%s (%s), %s : %s",
                                                str(nes[ne].get_string()), str(name), str(nes.keys()), nes[name],
                                                str(begin),
                                                str(stop))

                                    self.update_ne(begin, stop, nes[ne], sentence)

                                    sentence.add_ne(nes[ne])
                                elif name in nes.keys() and (
                                        begin != nes[ne].get_start_ind() and stop != nes[ne].get_end_ind()):
                                    logger.info("UPDATE [%s] Name %s in nes.keys()=%s (%s), %s : %s",
                                                str(nes[ne].get_string()), str(name), str(nes.keys()), nes[name],
                                                str(begin),
                                                str(stop))
                                    self.update_ne(begin, stop, nes[name], sentence)
                                    sentence.add_ne(nes[name])
                                else:
                                    nne = NamedEntity()
                                    nne.set_ne("", nes[ne].get_string(), begin, stop, nes[ne].get_type(), "finer")

                                    self.update_ne(begin, stop, nne, sentence)

                                    new_nes[name] = nne

                                    logger.info("Saving ne %s = %s : %s (%s-%s)", str(nne.get_string()), str(begin),
                                                str(stop), nne.get_start_char_index(), nne.get_end_char_index())

                                    sentence.add_ne(nne)
                                # add lookup for similar entities at same location, get also the words for each ne and
                                # possibly case for ne from the last word
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

    def update_ne(self, begin, stop, nne, sentence):

        end_word = sentence.get_word(stop)
        start_word = sentence.get_word(begin)

        logger.info('start word %s (%s = %s/%s)', start_word.get_word(), start_word.get_word(),
                    start_word.get_start_index(), begin)
        logger.info('end word %s (%s = %s/%s)', end_word.get_word(), end_word.get_word(), end_word.get_end_index(),
                    stop)

        # error happens here
        if len(nne.get_end_char_index()) > 0:
            if abs(nne.get_end_ind() - stop) < 4:
                nne.set_end_char_index(end_word.get_end_index())
                nne.set_document_end_char_index(
                    sentence.get_document_start_char_location() + start_word.get_start_index() + len(nne.get_string()))


            else:
                logger.warn("Cannot setting word end index %s != %s", str(nne.get_end_ind()), str(stop))
                logger.warn("Problem setting end index %s != %s for %s", str(nne.get_end_char_index()),
                            str(end_word.get_end_index()), str(nne))
        else:
            nne.set_end_char_index(end_word.get_end_index())
            nne.set_document_end_char_index(
                sentence.get_document_start_char_location() + start_word.get_start_index() + len(nne.get_string()))
            logger.info("Check if matches: %s", str(abs(nne.get_end_char_index()[0] - end_word.get_end_index())))

        if len(nne.get_start_char_index()) > 0:
            if abs(nne.get_start_ind() - begin) < 4:
                nne.set_start_char_index(start_word.get_start_index())
                nne.set_document_start_char_index(
                    sentence.get_document_start_char_location() + start_word.get_start_index())
            else:
                logger.warn("Cannot setting word end index %s != %s", str(nne.get_start_ind()), str(begin))
                logger.warn("Problem setting start index %s != %s for %s", str(nne.get_start_char_index()),
                            str(start_word.get_start_index()), str(nne))
        else:
            nne.set_start_char_index(start_word.get_start_index())
            nne.set_document_start_char_index(
                sentence.get_document_start_char_location() + start_word.get_start_index())
            logger.info("Check if matches: %s", str(abs(nne.get_start_char_index()[0] - start_word.get_start_index())))

        if nne.get_start_ind() == 0 and nne.get_end_ind() == 0:
            nne.set_start_ind([begin])
            nne.set_end_ind([stop])

        nne.set_related_words(sentence.list_words_between_indeces(begin, stop))

        logger.info("%s %s(%s %s %s), %s %s", nne.get_string(), ' LEN ', nne.get_start_char_index(), '-',
                    nne.get_end_char_index(), 'vrt. ', len(nne.get_string()))
        logger.info("[FINER] %s-%s in %s-%s", sentence.get_document_start_char_location(),
                    sentence.get_document_end_char_location(), nne.get_document_start_char_index(),
                    nne.get_document_end_char_index())

    def get_data(self):
        return self.orig_data

    def get_ne_dictionary(self):
        return self.ne_dictionary

    def __repr__(self):
        return "NerFiner"

    def __str__(self):
        return "NerFiner"


class ParseFinerResults(ParseResults):
    def __init__(self):
        self.nes = dict()
        self.ne_type_labels = {"EnamexOrgCrp": "OrganizationName", "EnamexPrsHum": "PersonName",
                               "TimexTmeDat": "ExpressionTime", "EnamexLocXxx": "PlaceName",
                               "EnamexLocStr": "AddressName", "EnamexLocPpl": "PoliticalLocation",
                               "EnamexLocGpl": "GeographicalLocation", "EnamexOrgEdu": "EducationalOrganization",
                               "EnamexOrgAth": "SportsOrganizations",
                               "EnamexOrgClt": "CultureOrganization", "EnamexOrgPlt": "PoliticalOrganization",
                               "EnamexOrgTvr": "MediaOrganization", "EnamexPrsTit": "Title",
                               "EnamexOrgFin": "FinnishOrganization",
                               "Exc": "Executive", "Event": "Event"}

    def parse(self, data, results):
        for k, v in results.items():
            if k in data:
                logger.info('found correct sentence %s (%s): %s', data[k], k, v)
                item = k
                value = v['entities']
                logger.debug('Item %s', item)
                logger.debug('Value %s', value)
                for res in value:
                    words = super().word_tokenizator(data[k])
                    logger.debug('start to parse: %s', res)
                    startA = int(res['word_start_index'])
                    endA = int(res['word_end_index'])

                    tag = res['category']
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

    def add_ne(self, first_ind, last_ind, name, tag, value):
        ne = NamedEntity()
        ne.set_ne("", value, first_ind, last_ind, tag, "finer")
        self.nes[name] = ne
        logger.info("Saving ne %s = %s : %s", str(ne.get_string()), str(first_ind), str(last_ind))

    def get_nes(self):
        return self.nes
