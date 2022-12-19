from src.nel.arpa.arpa import Arpa
from datetime import datetime
import json
import sys
import re
import traceback
from src.ner.namedentity import NamedEntity
import logging
import time
import datetime

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('arpa')


class ArpaConfig:
    def __init__(self, name="", url="", ordered=False):
        self.arpa_name = name
        self.arpa_url = url
        self.ordered = ordered

    def get_arpa_url(self):
        return self.arpa_url

    def set_arpa_url(self, url):
        self.arpa_url = url

    def get_arpa_name(self):
        return self.arpa_name

    def set_arpa_name(self, name):
        self.arpa_name = name

    def get_ordered(self):
        return self.ordered


class RunArpaLinker:
    def __init__(self, input_texts="", directory=""):
        self.input_texts = list()
        if len(input_texts) > 0:
            self.input_texts = input_texts

        self.configs = list()

        # results for all given texts
        self.results = dict()

        self.folder = directory
        if not (self.folder.endswith("/")):
            self.folder += "/"

        self.output_files = list()

    def set_input_texts(self, input_texts):
        if len(input_texts) > 0:
            self.input_texts = input_texts

    def set_config(self, config):
        if config not in self.configs:
            self.configs.append(config)

    def get_result(self):
        return self.results

    def run(self, multiprocess=False):
        import multiprocessing
        items = list(self.input_texts.items())
        if multiprocess:
            pool = multiprocessing.Pool(4)

            chunksize = 4
            chunks = [items[i:i + chunksize] for i in range(0, len(items), chunksize)]

            results = pool.map(self.run_linker_parallel, chunks)
            pool.close()
            pool.join()
            for d in results:
                self.results.update(d)
        else:
            start = time.time()
            logger.debug('Singleprocessing chunks: %s', items)
            results = self.run_linker_parallel(items)
            self.results = results
            end = time.time()
            logger.info("[STATUS] Executed Finer queries using single input in %s",
                        str(datetime.timedelta(seconds=(end - start))))

    def run_linker_parallel(self, data):
        tmp_results = dict()
        for tpl in data:
            ind = tpl[0]
            input_text = tpl[1]
            arpa_results = dict()  # results for each query for one text

            try:
                # for each text, perform arpa queries in predefined order
                for conf in self.configs:
                    logger.info("RUN CONF: %s %s", conf.get_arpa_name(), conf.get_arpa_url())
                    arpa = Arpa(conf.get_arpa_url(), conf.get_ordered())
                    if conf.get_arpa_name() in arpa_results:
                        arpa_results[conf.get_arpa_name()] = arpa_results[conf.get_arpa_name()] + self.do_arpa_query(
                            arpa, input_text)
                    else:
                        arpa_results[conf.get_arpa_name()] = self.do_arpa_query(arpa, input_text)
                tmp_results[ind] = arpa_results
                inds = ind.split("_")
                logger.info("Adding results for structure %s, paragraph %s, and sentence %s", inds[0], inds[0], inds[0])
            except Exception as e:
                logger.warning("Error: %s", e)
                logger.warning(sys.exc_info()[0])
                logger.warning("arpa_results: %s [%s]", str(arpa_results), str(ind))
                logger.error(traceback.format_exc())
        return tmp_results

    # Execute arpa queries
    def do_arpa_query(self, arpa, text):
        arpa_results = []
        parts = 0
        triple = dict()
        parts += 1

        q = self.stripInput(text)

        if len(q) > 0:
            result = arpa._query(q)
            if result is not None:
                # store the results
                triple['original'] = text
                triple['querystring'] = q
                logger.debug(result.text)
                if len(result.text):
                    try:
                        triple['arpafied'] = json.loads(result.text)
                        arpa_results.append(triple)
                    except Exception as e:
                        print("Unable to transform results to json")
                        logger.error("Unexpected error while transforming results to JSON: %s", e)
                        logger.warning("Unexpected error while transforming results: %s", result.text)

        return arpa_results

    # extract results from json to an python array
    def simplify_arpa_results(self, arpafied):
        simplified = dict()
        found = 0
        if arpafied is None:
            return None
        if 'results' in arpafied:
            results = arpafied['results']
            for result in results:
                if 'label' in result:
                    label = result['label']
                    if 'matches' in result:
                        matches = result['matches']
                        # logger.debug(matches)
                        for mlabel in matches:
                            # logger.debug(mlabel)
                            mlabel = mlabel.replace('"', '')
                            found = found + 1
                            if mlabel not in simplified:
                                labels = list()
                                labels.append(label)
                                simplified[mlabel] = labels
                            else:
                                if label not in simplified[mlabel]:
                                    simplified[mlabel].append(label)

                    elif 'properties' in result and 'ngram' in result['properties']:
                        original_string = result['properties']['ngram'][0]
                        found = found + 1
                        original_string = original_string.replace('"', '')
                        if original_string not in simplified:
                            labels = list()
                            labels.append(label)
                            simplified[original_string] = labels
                        else:
                            if label not in simplified[original_string]:
                                simplified[original_string].append(label)
        else:
            logger.warning("Results do not exist in arpafied, " + str(arpafied))
        return simplified, found

    # try to strip special characters and extra spaces from a string
    def stripInput(self, value):
        q = ""
        try:
            stripped = value.strip()
            qstr = stripped.format()
            q = re.sub('\s+', ' ', qstr)
            text = q.replace('*', '').replace('<', '').replace('>', '').replace('^', '').replace("@", '').replace(
                "+", '').replace("?", '').replace("_", '').replace("%", '').replace("'", "")
            q = text.replace('§', '').replace('[', '').replace(']', '').replace('{', '').replace("}", '').replace(
                "#", '').replace("~", '').replace('"', '').replace("+", '')
            q = q.replace('@', '').replace('$', '').replace('£', '').replace('µ', '').replace("!", '').replace("&",
                                                                                                               '').replace(
                '=', '').replace("|", '').replace(": ", ' ')

            q = q.replace('*', '').replace('^', '').replace("@", '').replace("+", '').replace("?", '').replace("_",
                                                                                                               '').replace(
                "%", '').replace("...", '').replace("|", '').replace("..", '').replace("■", '').replace("£", '')
            q = q.replace('•', '').replace('&', '').replace('´', '').replace('`', '').replace("§", '').replace("½",
                                                                                                               '').replace(
                "=", '').replace('¤', '').replace("$", '').replace("--", '').replace(",,", '').replace("»",
                                                                                                       '').replace(
                "—", '')
            q = q.replace('“', '').replace(' . ', ' ').replace("”", '').replace(".,", '').replace(',.', '').replace(
                "“", '').replace(",,,", '').replace("'", '').replace("«", '')
            q = re.sub(r'[\.,;-]{2}', "", q)
            # q = re.sub(r'[\.,;-]{2}', "", q)
            text = re.sub(r'\x85', 'â€¦', text)  # replace ellipses
            text = re.sub(r'\x91', "â€˜", text)  # replace left single quote
            text = re.sub(r'\x92', "â€™", text)  # replace right single quote
            text = re.sub(r'\x93', 'â€œ', text)  # replace left double quote
            text = re.sub(r'\x94', 'â€�', text)  # replace right double quote
            text = re.sub(r'\x95', 'â€¢', text)  # replace bullet
            text = re.sub(r'\x96', '-', text)  # replace bullet
            text = re.sub(r'\x99', 'â„¢', text)  # replace TM
            text = re.sub(r'\xae', 'Â®', text)  # replace (R)
            text = re.sub(r'\xb0', 'Â°', text)  # replace degree symbol
            text = re.sub(r'\xba', 'Â°', text)  # replace degree symbol

            text = re.sub('â€¦', '', text)  # replace ellipses
            text = re.sub('â€¢', '', text)  # replace bullet
            text = re.sub('â– ', '', text)  # replace squares
            text = re.sub('â„¢', '', text)  # replace TM
            text = re.sub('Â®', '', text)  # replace (R)
            text = re.sub('®', '', text)  # replace (R)
            text = re.sub('Â°', '', text)  # replace degree symbol
            text = re.sub('Â°', '', text)  # replace degree symbol

            q = re.sub(r'\d\d.\d\d.\d\d\d\d', "", q)  # dates
            text = re.sub(r'\d{1,2}.\d\d.', "", text)  # times

            # Do you want to keep new lines / carriage returns? These are generally
            # okay and useful for readability
            text = re.sub(r'[\n\r]+', ' ', text)  # remove embedded \n and \r

        except ValueError as err:
            logger.warning("Unexpected error while formatting document: %s", err)
            logger.warning("Error document content: %s" + value)
            q = value
        except Exception as e:
            logger.warning("Unexpected error while formatting document: %s", e)
            logger.warning("Error document content: %s" + value)
            q = value
        return q


def set_ne(ind, lemma, method, ne, ne_type, pattern_end, sentence, string):
    logger.debug("Setting NE for pattern %s,%s" % (ind, pattern_end))
    if ind == pattern_end:
        ne.set_ne("", string, ind, pattern_end, ne_type, method)
        end_word = sentence.get_word(pattern_end)
        start_word = sentence.get_word(ind)
        ne.set_related_words(sentence.list_words_between_indeces(ind, pattern_end))
        logger.debug('start word %s %s %s', start_word.get_word(), start_word.get_start_index(), ind)
        logger.debug('end word %s %s %s', end_word.get_word(), end_word.get_end_index(), pattern_end)
        ne.set_end_char_index(end_word.get_end_index())
        ne.set_document_end_char_index(
            sentence.get_document_start_char_location() + start_word.get_start_index() + len(string))
        ne.set_document_start_char_index(sentence.get_document_start_char_location() + start_word.get_start_index())
        ne.set_start_char_index(start_word.get_start_index())
        ne.set_case(end_word.get_case())
        ne.set_lemma(lemma)
    else:
        n = sum(1 for match in re.finditer('\s+', string))
        logger.debug("[%s] %s-%s", string, n, (pattern_end - ind))
        if (pattern_end - ind) == n:
            ne.set_ne("", string, ind, pattern_end, ne_type, method)
            end_word = sentence.get_word(pattern_end)
            start_word = sentence.get_word(ind)
            ne.set_related_words(sentence.list_words_between_indeces(ind, pattern_end))
            logger.debug('start word %s %s %s', start_word.get_word(), start_word.get_start_index(), ind)
            logger.debug('end word %s %s %s', end_word.get_word(), end_word.get_end_index(), pattern_end)
            ne.set_end_char_index(end_word.get_end_index())
            ne.set_start_char_index(start_word.get_start_index())
            ne.set_document_end_char_index(
                sentence.get_document_start_char_location() + start_word.get_start_index() + len(string))
            ne.set_document_start_char_index(
                sentence.get_document_start_char_location() + start_word.get_start_index())
            ne.set_case(end_word.get_case())
            ne.set_lemma(lemma)
        else:
            ne.set_ne("", string, ind, pattern_end - 1, ne_type, method)
            end_word = sentence.get_word(pattern_end - 1)
            start_word = sentence.get_word(ind)
            ne.set_related_words(sentence.list_words_between_indeces(ind, pattern_end - 1))
            logger.debug('start word %s %s %s', start_word.get_word(), start_word.get_start_index(), ind)
            logger.debug('end word %s %s %s', end_word.get_word(), end_word.get_end_index(), pattern_end - 1)
            ne.set_end_char_index(end_word.get_end_index())
            ne.set_start_char_index(start_word.get_start_index())
            ne.set_document_end_char_index(
                sentence.get_document_start_char_location() + start_word.get_start_index() + len(string))
            ne.set_document_start_char_index(
                sentence.get_document_start_char_location() + start_word.get_start_index())
            ne.set_case(end_word.get_case())
            ne.set_lemma(lemma)


class NamedEntityLinking:
    def __init__(self, data, input_data):

        self.input_data = data

        if input_data is None:
            self.input_texts = self.create_ner_input_data(data)
        else:
            self.input_texts = input_data

        self.folder = "/u/32/tamperm1/unix/python-workspace/nerdl/input/"
        self.linker = RunArpaLinker(directory=self.folder)

    def create_ner_input_data(self, doc):
        data = dict()
        structure = doc.get_structure()
        for structu_id, parval in structure.get_structures().items():
            parid = parval.get_id()
            for sid, sentence in parval.get_sentences().items():
                ind = str(structu_id) + "_" + str(parid) + "_" + str(sid)
                data[ind] = " ".join([word.get_word() for word in list(sentence.get_words().values())])
        return data

    def create_configuration(self, name, url, ordered):
        if len(url) > 0:
            config = ArpaConfig(name, url, ordered)
            self.linker.set_config(config)

    def exec_linker(self):
        result_data = dict()
        # process documents one by one, one sentence at the time
        if self.linker is None:
            self.linker = RunArpaLinker(self.input_texts, self.folder)
        else:
            self.linker.set_input_texts(self.input_texts)
        self.linker.run()
        result = self.parse_results(self.linker.get_result())
        result_data.update(result)
        self.write_nes(result_data)

    def parse_results(self, results):
        result_set = dict()
        # parse for each sentence the results of each query
        for result in results.keys():
            l = list()
            query_results = dict()
            logger.debug(result)
            # parse and add from each arpa query
            for query_name, query_result in results[result].items():
                query_results[query_name] = list()
                for data in query_result:
                    arpafied = data["arpafied"]
                    tempD = dict()
                    for arpa_result in arpafied['results']:
                        str_label = ""
                        str_matches = ""
                        link = ""
                        wp = ""
                        # now taking only the first result, in near future expand to take it all !

                        properties = arpa_result["properties"]
                        matches = arpa_result["matches"]
                        label = arpa_result["label"]

                        logger.info(properties)
                        if label is not None:
                            str_label = label

                        if matches is not None:
                            str_matches = matches[0]

                        if "source" in properties:
                            link = properties["source"][0].replace("<", "").replace(">", "")
                            logger.info(properties["source"])

                        if "wikipedia" in properties:
                            wp = properties["wikipedia"][0].replace("<", "").replace(">", "")
                            logger.info(properties["wikipedia"])

                        id = properties["id"][0].replace("<", "").replace(">", "")
                        tempD[(str_label, id)] = (str_matches, str_label, id, link, wp, query_name)
                    if len(list(tempD.keys())) > 0:
                        keys = list(tempD.keys())

                        for key in keys:
                            tpl = tempD[key]
                            query_results[query_name].append(tpl)

                    for k in sorted(list(query_results.keys())):
                        l.extend(query_results[k])
            result_set[result] = l

        return result_set

    def write_nes(self, nes):
        logger.info("writing nes")
        STRUCT_ID = 0
        PAR_ID = 1
        SEN_ID = 2
        MATCHES = 0
        LABEL = 1
        ID = 2
        LINK = 3
        WP = 4
        TYPE = 5
        necounter = 0
        for ne in nes.keys():
            parts = ne.split("_")
            logger.info("For key %s", ne)
            logger.info("%s transforms to %s", ne, parts)

            ne_struct_id = parts[STRUCT_ID]
            ne_parag_id = parts[PAR_ID]
            ne_sen_id = parts[SEN_ID]

            triples = nes[ne]

            for triple in triples:
                logger.info("got triple: %s", triple)
                structures = self.input_data.get_structure().get_structures()
                for struct_id, struct in structures.items():
                    if int(struct_id) == int(ne_struct_id):
                        if struct is not None:
                            sentence = struct.get_sentence(ne_sen_id)

                            dct = sentence.find_word_ind(triple[MATCHES].strip().split())
                            start = list(dct.keys())
                            end = list(dct.values())
                            logger.debug("(DEBUG) %s, %s" % (start, end))
                            if start is None and end is None:
                                dct = sentence.find_word_ind(list(reversed(nes[ne].get_string().strip().split())))
                                start = list(dct.keys())
                                end = list(dct.values())

                            if start is None and end is None:
                                dct = sentence.find_word_ind(nes[ne].get_string().strip().replace(".", " .").split())
                                start = list(dct.keys())
                                end = list(dct.values())

                            if start is not None and end is not None:
                                logger.warning('Add %s (%s-%s) for sentence %s', triple[MATCHES].strip().split(), start,
                                               end, sentence.get_sentence_string())

                                # add char locations
                                for i, j in enumerate(start):
                                    related = None
                                    begin = start[i]
                                    stop = end[i]
                                    logger.debug("%s:%s", begin, stop)
                                    end_word = sentence.get_word(stop)
                                    start_word = sentence.get_word(begin)

                                    entity_type = triple[TYPE]
                                    if '_' in triple[TYPE]:
                                        entity_type = triple[TYPE].split('_')[0]

                                    ne = self.create_named_entity(begin, stop, sentence, entity_type, "arpa", 1,
                                                                  triple[LABEL], start, start_word, end, end_word,
                                                                  related=related, linked=triple[ID])
                                    if len(triple[LINK]) > 0:
                                        ne.add_related_links(triple[LINK])
                                    if len(triple[WP]) > 0:
                                        ne.add_related_links(triple[WP])

                            else:
                                logger.warning("Could not find ne %s %s", str(nes[ne]),
                                               nes[ne].get_string().strip().replace(".", " ."))
                                logger.warning("For sentence %s", str(sentence.get_words()))

    def create_named_entity(self, ind, pattern_end, sentence, ne_type, method, score, lemma, start, start_word, end,
                            end_word, related=None, linked=None):
        logger.debug("create_named_entity: %s:%s (%s)" % (ind, pattern_end, lemma))
        end = int(pattern_end)
        string, words = sentence.get_named_entity_string(ind, end)

        # add checkup for existing similar entity at same location
        ne = sentence.get_similar_named_entities_at(ind, pattern_end, string, ne_type)

        if ne is None:
            # Add completely new named entity
            ne = NamedEntity()
            logger.debug("New NE: %s, %s, %s" % (string, lemma, words))

            set_ne(ind, lemma, method, ne, ne_type, pattern_end, sentence, string)
        else:
            # If there exists already same or similar entity...
            if ne.get_type() != ne_type:
                logger.debug(
                    "but the type is different and still related to each other (e.g. PlaceName vs. GeographicalLocation)")
                # but the type is different and still related to each other (e.g. PlaceName vs. GeographicalLocation)
                # ... but the type is different and still related to each other (e.g. PlaceName vs. GeographicalLocation)
                nes = ne
                nes.set_method(method, score)
                nes.set_simple_type_score()
                nes.add_related_match(lemma, linked)
                ne = NamedEntity()
                set_ne(ind, lemma, method, ne, ne_type, pattern_end, sentence, string)
                ne.set_simple_type_score()
            elif ne.get_string() != string and ne.get_type() == ne_type:
                logger.debug(
                    "but the string label is different and the type is the same (e.g. Sauli Väinämö Niinistö and Väinämä Niinistö)")
                # but the string label is different and the type is the same (e.g. Sauli Väinämö Niinistö and Väinämä Niinistö)
                # ... but the string label is different and the type is the same (e.g. Sauli Väinämö Niinistö and Väinämä Niinistö)
                nes = ne
                nes.set_method(method, score)
                nes.set_simple_type_score()
                nes.add_related_match(lemma, linked)
                ne = NamedEntity()
                set_ne(ind, lemma, method, ne, ne_type, pattern_end, sentence, string)
                ne.set_simple_type_score()
            else:
                # but it is the same entity, just update the existing
                # ... but it is the same entity, just update the existing
                logger.debug("but it is the same entity, just update the existing")
                end_word = sentence.get_word(pattern_end)
                start_word = sentence.get_word(ind)
                logger.debug("[DEBUG] %s, %s (%s, %s)" % (start_word, end_word, ind, pattern_end))
                if len(ne.get_related_words()) < 1:
                    ne.set_related_words(sentence.list_words_between_indeces(ind, pattern_end))
                if ne.get_end_char_index() == 0:
                    ne.set_end_char_index(end_word.get_end_index())
                    ne.set_document_end_char_index(
                        sentence.get_document_start_end_location() + end_word.get_end_index())
                if ne.get_start_char_index() == 0:
                    ne.set_start_char_index(start_word.get_start_index())
                    ne.set_document_start_char_index(
                        sentence.get_document_start_char_location() + start_word.get_start_index())
                ne.set_case(end_word.get_case())
                ne.set_lemma(lemma)
                logger.debug("End char index: %s", str(ne.get_end_char_index()))
                logger.debug("End char document index: %s", str(ne.get_document_end_char_index()))
                logger.debug('start word %s %s %s', start_word.get_word(), start_word.get_start_index(), ind)
                logger.debug('end word %s %s %s', end_word.get_word(), end_word.get_end_index(), pattern_end - 1)

        ne.add_related_match(lemma, linked)
        ne.set_method(method, score)
        if related is not None:
            ne.set_related(related)

        # Add sentence
        sentence.add_ne(ne)

        return ne
