from src.ner.depparser.run_depparser import RunDepParser
from src.ner.namedentity import NamedEntity
from src.ner.nerregex import NerRegEx
from src.structure.morphologicalfeatures import MorphologicalFeatures
import logging
from src.ner.parse_results import Ner, ParseResults

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('depparser')


class NerDepParser(Ner):
    def __init__(self, data, text_data, ne_dictionary=None):
        tool, pool_size, pool_number, level, lemmatize = super().read_configs('DEPPARSER')

        if ne_dictionary is None:
            self.ne_dictionary = dict()
        else:
            self.ne_dictionary = ne_dictionary

        self.orig_data = data
        if text_data is None:
            self.input_data = super().create_ner_input_data(data, level=level)
        else:
            self.input_data = text_data  # self.create_ner_input_data
        self.document_level_data = super().create_ner_input_data(data, level=2)

        self.tool = tool
        self.pool_size = pool_size
        self.pool_number = pool_number
        self.lemmatize = lemmatize
        self.level = level

    def run_tool(self, linfer=False):

        input_data_by_level = self.document_level_data
        logger.debug("[DEPPARSER] run-tool %s", self.input_data)
        dpParser = ParseDepParserResults(self.orig_data)
        depparser = RunDepParser("", "", self.tool, self.input_data, self.pool_number, self.pool_size, self.level)
        if self.level == 1:
            depparser.run(multiprocess=False)
        else:
            depparser.run(multiprocess=True)

        if self.level == 2:
            input_data_by_level = self.input_data
        dpParser.parse(input_data_by_level, depparser.get_output_files())

        if linfer:
            # identify and write nes to sentences
            ner = NerRegEx()
            ner.identify([self.orig_data.get_structure()])

        self.orig_data.set_morphological_analysis_results(depparser.get_output_files(), str(self))

    def write_nes(self, nes):
        STRUCT_ID = 0
        PAR_ID = 1
        SEN_ID = 2
        necounter = 0
        start = None
        end = None

        logger.info('WRITE NES')
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
                logger.debug("%s, %s, %s", ne_struct_id, struct_id, struct)
                if int(struct_id) == int(ne_struct_id):

                    if struct != None:
                        sentence = struct.get_sentence(ne_sen_id)
                        dct = sentence.find_word_ind(nes[ne].get_string().strip().split())
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

                        if start != None and end != None:
                            logger.info('Add for sentence %s %s-%s', sentence.get_sentence_string(), start, end)
                            nes[ne].set_start_ind(start)
                            nes[ne].set_end_ind(end)

                            # add char locations
                            for i, j in enumerate(start):
                                logger.debug("[DEPPARSER] write nes: %s, %s", i, start)
                                begin = start[i]
                                stop = end[i]
                                end_word = sentence.get_word(stop)
                                start_word = sentence.get_word(begin)
                                nes[ne].set_end_char_index(end_word.get_end_index())
                                nes[ne].set_start_char_index(start_word.get_start_index())
                                nes[ne].set_document_end_char_index(
                                    sentence.get_document_end_char_location() + end_word.get_end_index())
                                nes[ne].set_document_start_char_index(
                                    sentence.get_document_start_char_location() + start_word.get_start_index())

                                sentence.add_ne(nes[ne])

                        else:
                            logger.warning("Could not find ne %s %s", str(nes[ne]),
                                           nes[ne].get_string().strip().replace(".", " ."))
                            logger.warning("For sentence %s", str(sentence.get_words()))
                    else:
                        logger.warning('Unidentifiable struct: %s', str(struct))

    def get_data(self):
        return self.orig_data

    def get_ne_dictionary(self):
        return self.ne_dictionary

    def __repr__(self):
        return "NerDepParser"

    def __str__(self):
        return "NerDepParser"


class ParseDepParserResults(ParseResults):
    def __init__(self, data):
        self.data = data
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
            logger.debug("[DEPPARSER] parse k,v: %s, %s", k, v)
            logger.debug("[DEPPARSER] parse %s", data)
            if k in data:
                # logger.info('[PARSE] Found correct sentence %s for %s (%s)', data[k], k, v['text'])
                value = v
                if 'words' in value:
                    for res in value['words']:
                        logger.info('[PARSE] Result: %s', res)
                        id = res['ID']
                        form = res['FORM']
                        lemma = res['LEMMA']
                        upos = res['UPOS']
                        xpos = res['XPOS']
                        edge = res['EDGE']
                        head = res['HEAD']
                        deprel = res['DEPREL']
                        deps = res['DEPS']
                        misc = res['MISC']
                        feats = self.parse_feats(res['FEATS'])

                        structid, parid, sid = k.split('_')
                        sentence = self.find_sentence(structid, parid, int(sid))
                        logger.info("[PARSE] Found sentence (%s) %s (for %s):", k, sentence, value['text'])

                        if sentence != None:
                            sentence.set_word_feats(id - 1, form, lemma, upos, xpos, edge, head, deprel, deps, misc,
                                                    feats)
                        else:
                            logger.warn("[PARSE] Cannot find sentence ", sentence, k, structid, parid, sid)

                        sentence.lemmatize_nes()
            else:
                logger.info("[PARSE] Result parsing: cannot find correct sentence %s, %s", k, data)

    def parse_feats(self, feats):
        morp = MorphologicalFeatures()
        morp.parse(feats)
        return morp

    def find_sentence(self, structid, parid, sid):
        logger.info("[FIND SENTENCE] For %s, %s, %s", structid, parid, sid)
        struct = self.data.get_structure()
        for structu_id, pars in struct.get_structures().items():
            if int(structid) == int(structu_id):
                logger.info("[FIND SENTENCE] For %s, %s = %s?", structid, pars, parid)
                sens = pars.get_sentences()
                if int(sid) in sens:
                    return sens[sid]
        return None

    def add_ne(self, first_ind, last_ind, name, tag, value):
        ne = NamedEntity()
        ne.set_ne("", value, first_ind, last_ind, tag, "depparser")
        self.nes[name] = ne

    def get_nes(self):
        return self.nes

    def __str__(self):
        return type(self).__name__
