from src.ner.las.run_las import RunLas
from src.ner.namedentity import NamedEntity
from src.ner.nerregex import NerRegEx
from src.structure.morphologicalfeatures import MorphologicalFeatures
import logging
from src.ner.parse_results import Ner, ParseResults

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('las')


class NerLas(Ner):
    def __init__(self, data, text_data, ne_dictionary=None):
        logger.debug("[LAS] INIT: %s, %s",data, text_data)
        tool, pool_size, pool_number, level, lemmatize = super().read_configs('LASWRAPPER')
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

    def run_tool(self, linfer=True):
        lasResults = ParseLasResults(self.orig_data)
        las = RunLas("","",self.tool, self.input_data, self.pool_number, self.pool_size)
        las.run(multiprocess=True)
        lasResults.parse(self.input_data,las.get_output_files())

        if linfer:
            # identify and write nes to sentences
            ner = NerRegEx()
            ner.identify([self.orig_data.get_structure()])

        self.orig_data.set_morphological_analysis_results(las.get_output_files(), str(self))
        logger.info("[LAS] Ending processing")

        return None

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
            for structu_id,struct in structures.items():
                if int(structu_id) == int(structid):

                    if struct != None:
                        sentence = struct.get_sentence(senid)
                        dct = sentence.find_word_ind(nes[ne].get_string().strip().split())
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

                        if start != None and end != None:
                            logger.info('Add for sentence %s (%s:%s), %s', sentence.get_sentence_string(), start, end, nes[ne].get_string())
                            nes[ne].set_start_ind(start)
                            nes[ne].set_end_ind(end)

                            # add char locations
                            for i,j in enumerate(start):
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
                            logger.warning("Could not find ne %s %s", str(nes[ne]), nes[ne].get_string().strip().replace(".", " ."))
                            logger.warning("For sentence %s", str(sentence.get_words()))
                    else:
                        logger.warning('Unidentifiable struct: %s', str(struct))

    def get_data(self):
        return self.orig_data

    def get_ne_dictionary(self):
        return self.ne_dictionary

    def __repr__(self):
        return "NerLas"

    def __str__(self):
        return "NerLas"

class ParseLasResults(ParseResults):
    def __init__(self, data):
        self.data = data
        self.nes = dict()
        self.ne_type_labels = {"EnamexOrgCrp": "OrganizationName", "EnamexPrsHum": "PersonName",
                               "TimexTmeDat": "ExpressionTime", "EnamexLocXxx": "PlaceName",
                               "EnamexLocStr": "AddressName", "EnamexLocPpl": "PoliticalLocation",
                               "EnamexLocGpl": "GeographicalLocation", "EnamexOrgEdu": "EducationalOrganization",
                               "EnamexOrgAth":"SportsOrganizations",
                               "EnamexOrgClt":"CultureOrganization", "EnamexOrgPlt":"PoliticalOrganization",
                               "EnamexOrgTvr":"MediaOrganization", "EnamexPrsTit":"Title", "EnamexOrgFin": "FinnishOrganization",
                               "Exc":"Executive", "Event":"Event"}

    def parse(self, sentence_data, results):
        logger.info("[LAS] Start to parse")
        status = None
        prev_id = -1
        logger.info("[LAS] Results:%s" % results)
        for key, res in results.items():
            for v in res['morphology']:
                k = v['paragraph']
                item = v['sentence']
                senid = str(k)+"_"+str(k)+"_"+str(item)
                logger.info("Check if %s in keys %s", senid, sentence_data.keys())
                if senid in sentence_data.keys():
                    logger.info('Found correct sentence %s %s', sentence_data[senid], v)
                    for res in v['words']:
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

                        sentence = self.find_sentence(k, k, int(item))
                        logger.info('Result: %s. %s (%s or %s)', id, form, sentence_data[senid], sentence)

                        if sentence != None:
                            if status == -1 and upos in ['NUM', 'PUNCT']:
                                status = sentence.set_word_feats(prev_id, form, lemma, upos, xpos, edge, head,
                                                                 deprel, deps, misc, feats)
                            else:
                                status = sentence.set_word_feats(id-1, form, lemma, upos, xpos, edge, head, deprel, deps, misc, feats)
                        else:
                            logger.warning("[WARN] Cannot find sentence %s, K=%s, ITEM=%s",sentence, k, item)

                        prev_id = id
                else:
                    logger.warning("WARN %s not in data %s", k, sentence_data)

    def parse_feats(self, feats):
        morp = MorphologicalFeatures()
        morp.parse(feats)
        return morp

    def find_sentence(self, structid, parid, sid):
        struct = self.data.get_structure()
        for structu_id, pars in struct.get_structures().items():
            if int(structid) == int(structu_id):
                sens = pars.get_sentences()
                if int(sid) in sens:
                    return sens[sid]
        return None

    def add_ne(self, first_ind, last_ind, name, tag, value):
        ne = NamedEntity()
        ne.set_ne("", value, first_ind, last_ind, tag, "finer")
        self.nes[name] = ne

    def get_nes(self):
        return self.nes

    def __str__(self):
        return type(self).__name__