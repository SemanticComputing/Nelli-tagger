from src.structure.sentence import Sentence
from src.structure.word import Word

from src.ner.namedentity import NamedEntity
from src.structure.paragraph import Paragraph
from src.structure.title import Title
import logging.config
from xml.etree import ElementTree as ET
import traceback

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('doc')


class Structure:
    def __init__(self):
        self.structures = dict()
        self.paragraphs = dict()
        self.titles = dict()
        self.id = ""
        self.struct_elem = None

    def get_id(self):
        return self.id

    def get_structure_element(self):
        return self.struct_elem

    def set_structure_element(self, elm):
        self.struct_elem = elm.getroot()

    def parse(self, input):
        words = dict()
        word, upos, feat, edge, id, prev_id, sId, s_uri = "", "", "", "", "", "", 1, 1
        ne_uri, type_uri, begin, end, string = None, "", "", "", ""
        ne = None
        pid = 1
        start = 0

        # sentence for paragraph
        sentence = Sentence()
        paragraph = Paragraph()

        for result in input["results"]["bindings"]:
            prev_id = int(sId)
            prev_par = int(pid)
            sId = float(result["y"]["value"])
            pid = int(result["z"]["value"])
            test = result["paragraph"]["value"]

            if start == 0:
                paragraph.set_paragraph(pid, None)
                start = 1

            if sId != prev_id or pid != prev_par:
                # change sentence
                sentence.set_sentence(prev_id, sId, None, words, s_uri)
                paragraph.add_sentence(prev_id, sentence)
                sentence = Sentence()
                words = dict()

            if pid != prev_par:
                self.structures[prev_par] = paragraph
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
        paragraph.add_sentence(pid, sentence)
        self.structures[pid] = paragraph

    def get_paragraphs(self):
        return self.paragraphs

    def get_titles(self):
        return self.titles

    def get_structures(self):
        return self.structures

    def get_titles(self):
        return self.titles

    def print_nes(self):
        for pid in self.structures:
            paragraph = self.structures[pid]
            paragraph.print_nes()

    def get_sentences(self):
        for pid in self.structures:
            paragraph = self.structures[pid]
            paragraph.get_sentences()

    def get_structure(self, pid):
        for struct_id in self.structures.keys():
            if int(struct_id) == int(pid):
                return self.structures[struct_id]

    def get_title(self, pid):
        for title_id in self.paragraphs.keys():
            if int(title_id) == int(pid):
                return self.paragraphs[title_id]

    def get_paragraph(self, pid):
        for parg_id in self.titles.keys():
            if int(parg_id) == int(pid):
                return self.titles[parg_id]

        return None

    def set_structure(self, id, paragraphs):
        self.id = id
        self.structures = paragraphs

    def add_structure(self, id, obj):
        if self.structures is None:
            self.structures = dict()
        if id is not None and obj is not None:
            self.structures[id] = obj

    def set_title(self, id, title):
        if self.titles is None:
            self.titles = dict()
        if id is not None and title is not None:
            self.titles[id] = title

    def set_paragraph(self, id, paragraph):
        if self.paragraphs is None:
            self.paragraphs = dict()
        if id is not None and paragraph is not None:
            self.paragraphs[id] = paragraph

    def get_structure_id(self):
        return self.id

    def get_id_ending(self):
        return self.id.split('/')[-1]

    def print_nes(self):
        logger.info('Printing paragraphs and titles %s', str(self.structures))
        for i, j in self.structures.items():
            logger.info(str(i))
            logger.info(str(self.structures[i]))
            logger.info('item: %s %s', str(i), str(j))
            for id, s in j.get_sentences().items():
                logger.info("%s %s" % (str(id), str(s)))

    def render_text(self, id, setup=None):
        document = ""
        for i, j in self.structures.items():
            if type(j) == Title:
                logger.debug("Title identified, skipping!!!!")
            elif type(j) == Paragraph:
                id, text = self.render_paragraph_text(j, id, setup=setup)
                document += text + '\n'
            else:
                logger.warning('Unidentified struct %s', str(j))
        return document

    def render_html(self, id, setup=None):
        for i, j in self.structures.items():
            if type(j) == Title:
                logger.debug("Title identified, skipping!!!!")
            elif type(j) == Paragraph:
                id = self.render_paragraph_html(j, id, setup=setup)
            else:
                logger.warning('Unidentified struct %s', str(j))
        return ET.tostring(self.struct_elem, method='html', encoding='utf-8').decode(
            'utf8')  

    def render_xml(self, id, setup=None):
        for i, j in self.structures.items():
            if type(j) == Title:
                logger.debug("Title identified, skipping!!!!")
            elif type(j) == Paragraph:
                id = self.render_paragraph_html(j, id, setup=setup)
            else:
                logger.warning('Unidentified struct %s', str(j))
        return ET.tostring(self.struct_elem, method='xml',
                           encoding='utf-8')  

    def render_html_xml(self, id, setup=None):

        prev_struct = None
        master_div = ET.Element('div')
        div = None
        prev_title = None
        prev_div = None
        for i, j in self.structures.items():
            if type(j) == Title:
                # first title
                if prev_struct is None:
                    prev_div = master_div
                    div = ET.SubElement(prev_div, 'div')
                    header, id = self.render_title_html(j, div, id, setup=setup)
                    prev_struct = j
                    prev_title = j
                # if two titles
                elif type(j) == Title and type(prev_struct) == Title:
                    logger.info('Compare: %s AND %s', str(j.get_level()), str(prev_struct.get_level()))
                    # j = h3, prev_title = h2
                    if self.header_comparison(j, prev_title) == j:  # j.get_level() < prev_struct.get_level():
                        # save new title into new div
                        prev_div = div
                        div = ET.SubElement(prev_div, 'div')
                        header, id = self.render_title_html(j, div, id, setup=setup)
                        prev_struct = j
                        prev_title = j
                    # j = h3, prev_title = h2
                    elif self.header_comparison(j, prev_title) == prev_title:
                        parent = div.find('..')
                        if parent is None:
                            parent = master_div
                        logger.info('Parent %s of element %s', str(parent), str(div))
                        prev_div = div
                        div = ET.SubElement(parent, 'div')
                        header, id = self.render_title_html(j, div, id, setup=setup)
                        prev_title = j
                    else:
                        logger.info('two headers with same level!? %s and %s', str(prev_struct), str(j))
                # new big title, j = h2, prev_title = h3
                elif self.header_comparison(j, prev_title) == prev_title or self.header_comparison(j,
                                                                                                   prev_title) is None:
                    logger.info('Compare: %s VS %s', str(j.get_level()), str(prev_title.get_level()))
                    parent = div.find('..')
                    if parent is None:
                        parent = master_div
                        logger.info('Parent %s of element %s', str(parent), str(div))
                    prev_div = div
                    div = ET.SubElement(parent, 'div')
                    header, id = self.render_title_html(j, div, id, setup=setup)
                    prev_div = div
                    div = ET.SubElement(prev_div, 'div')
                    prev_title = j
                elif type(j) == Title:
                    logger.info("%s %s", j, type(j))
                    if type(prev_struct) == Title:
                        header, id = self.render_title_html(j, div, id, setup=setup)
                    else:
                        header, id = self.render_title_html(j, div, id, setup=setup)
                    prev_struct = j
                elif type(j) == Paragraph:
                    p, id = self.render_paragraph_xml(j, div, id, setup=setup)
                    prev_struct = j
                else:
                    logger.warning('Unidentified struct %s', str(j))
            elif type(j) == Paragraph:
                p, id = self.render_paragraph_xml(j, div, id, setup=setup)
                prev_struct = j
            else:
                logger.warning('Unidentified struct %s', str(j))

        return ET.tostring(master_div, encoding='utf8').decode('utf8')

    def header_comparison(self, a, b):
        alevel = a.get_level().replace('h', '')
        blevel = b.get_level().replace('h', '')

        if alevel > blevel:
            return a
        elif blevel > alevel:
            return b
        else:
            return None

    def render_title_html(self, title, master, id, setup=None):
        header = None
        if title.get_level() == "h2":
            header = ET.SubElement(master, 'h2')
        elif title.get_level() == "h3":
            header = ET.SubElement(master, 'h3')
        elif title.get_level() == "h4":
            header = ET.SubElement(master, 'h4')
        elif title.get_level() == "h5":
            header = ET.SubElement(master, 'h5')
        elif title.get_level() == "h6":
            header = ET.SubElement(master, 'h6')
        else:
            logger.warning('Unknown header %s', title.get_level())

        logger.debug('debug %s %s', header, title)
        logger.debug('string %s', title.get_title_string())
        header.text, id = title.render_html(master, id, setup=setup)
        return header, id

    def render_paragraph_xml(self, paragraph, master, id, setup=None):
        p = ET.SubElement(master, 'p')
        logger.info('[XML] Rendered paragraph: %s %s', p, paragraph)
        p.text, id = paragraph.render_html(p, id, setup=setup)
        return p, id

    def render_paragraph_html(self, paragraph, id, setup=None):
        id = paragraph.render_html(id, setup=setup)
        return id

    def render_paragraph_text(self, paragraph, id, setup=None):
        text, idx = paragraph.render_text(id, setup=setup)
        return id, text

    def get_named_entities_list(self):
        entities = list()
        for i, struct in self.structures.items():
            for id, s in struct.get_sentences().items():
                entities.extend(s.get_nes())
        return entities

    def get_named_entities_json_list(self, return_uniques=True, setup=None):
        # create a list of named entities in json format, apply grouping for names
        entities = list()
        context = 0

        for i, struct in self.structures.items():
            for id, s in struct.get_sentences().items():
                entities.extend(s.get_json_nes(disambiguate=True, setup=setup))

        logger.info("Entities: %s", entities)

        # group named entities based on string, lemma
        uniques, all = self.resetentity_ids(entities, id=1)

        # disambiguate references to names and regroup them
        self.reset_name_ids(entities, id=1)
        self.reset_org_ids(entities, id=1)

        if 'nf_context' in setup.keys():
            context = setup['nf_context']
        else:
            print(setup.keys())

        if return_uniques:
            logger.debug("[GET UNIQUE ENTITIES] Unique entities: %s", uniques)
            return self.render_entities_json(uniques, context=context)

        logger.debug("[GET ALL ENTITIES] All entities: %s", all)
        return self.render_entities_json(all, context=context)

    def check(self, entity, key_list):
        # check if entity exists in a list of entities

        for item in key_list:
            if (item.get_string().lower().strip() == entity.get_string().lower().strip() or (
                    item.get_lemma().lower().strip() == entity.get_lemma().lower().strip()) and len(
                    entity.get_lemma()) > 1 and len(item.get_lemma()) > 1):
                if item.get_type().lower().strip() == entity.get_type().lower().strip() or item.get_simple_type() == entity.get_simple_type():
                    return item
                else:
                    return None
        return None

    def resetentity_ids(self, entities, id=0):
        # group entities based on string similarity

        idmap = dict()
        for ne in entities:

            exists = self.check(ne, idmap.keys())
            if exists is not None:
                ne.set_id(idmap[exists])
            else:
                ne.set_id(id)
                idmap[ne] = id
                id += 1

        logger.info("%s", idmap)

        return list(idmap.keys()), entities

    def reset_org_ids(self, entities, id=0):
        # apply grouping for names and identify references to people based on names.
        # Steps:
        # 1. divided names to long (full names with all first names and last names),
        #    average (typically first name and last name), short (last names or first names)
        # 2. check for average names that contain a reference to a short name (e.g. Sanoma and Sanoma Media)
        # 3. check for average names that contain a reference to a short name (e.g. Sanoma Media and Sanoma Media Finland)

        ne_org_names = [ne for ne in entities if ne.get_simple_type() == 'OrganizationName']
        short_names = [ne for ne in ne_org_names if ne.get_word_count() == 1]
        avg_names = [ne for ne in ne_org_names if ne.get_word_count() == 2]
        avg_string_names = [ne.get_lemma().split(' ')[0] for ne in avg_names if
                            ne.get_word_count() == 2]

        self.find_related_names(avg_names, avg_string_names, short_names)

        longest_names = [ne for ne in ne_org_names if ne.get_word_count() > 2]
        longest_string_names = [str(ne.get_lemma().split(' ')[0] + " " + ne.get_lemma().split(' ')[1]) for ne in
                                longest_names if
                                ne.get_word_count() > 2]

        for ne in avg_names:
            try:
                if len(ne.get_lemma().split(' ')) > 1:
                    name = ne.get_lemma().split(' ')[0] + " " + ne.get_lemma().split(' ')[1]
                    if name in longest_string_names:
                        ind = self.find_most_relevant_index(longest_names, longest_string_names, ne, name)
                        longest_names[ind].set_id(ne.get_id())
                        ne.set_related(longest_names[ind])
                        longest_names[ind].set_related(ne)
                else:
                    logger.warning("Unable to split and find relatives for name %s (%s)", ne.get_string(),
                                   ne.get_lemma())
            except Exception as err:
                logger.warning("Unable to split and find relatives for name %s (%s)", ne.get_string(), ne.get_lemma())
                logger.error(err)

    def reset_name_ids(self, entities, id=0):
        # apply grouping for names and identify references to people based on names.
        # Steps:
        # 1. divided names to long (full names with all first names and last names),
        #    average (typically first name and last name), short (last names or first names)
        # 2. check for average names that contain a reference to a short name (e.g. Niinistö and Sauli Niinistö)
        # 3. check for average names that contain a reference to a short name (e.g. Sauli and Sauli Niinistö)
        # 4. check relations between longest names and average names (e.g. Sauli Niinistö and Sauli Väinämö Niinistö)
        # 5. check relations between longest and shortest names (e.g. Niinistö and Sauli Väinämö Niinistö)

        ne_person_names = [ne for ne in entities if ne.get_type() == 'PersonName']
        short_names = [ne for ne in ne_person_names if ne.get_word_count() == 1]
        avg_names = [ne for ne in ne_person_names if ne.get_word_count() == 2]
        avg_string_names = [ne.get_lemma().split(' ')[-1] for ne in avg_names if
                            ne.get_word_count() == 2]

        self.find_related_names(avg_names, avg_string_names, short_names)

        avg_string_names = [ne.get_lemma().split(' ')[0] for ne in avg_names if
                            ne.get_word_count() == 2]

        for ne in short_names:
            name = ne.get_lemma()
            if name in avg_string_names:
                ind = self.find_most_relevant_index(avg_names, avg_string_names, ne, name)
                ne.set_id(avg_names[ind].get_id())
                ne.set_related(avg_names[ind])
                avg_names[ind].set_related(ne)

        longest_names = [ne for ne in ne_person_names if ne.get_word_count() > 2]
        avg_string_names = [ne.get_lemma() for ne in avg_names if
                            ne.get_word_count() == 2]

        for ne in longest_names:
            name = ne.get_lemma().split(' ')[0] + " " + ne.get_lemma().split(' ')[-1]
            if name in avg_string_names:
                ind = self.find_most_relevant_index(avg_names, avg_string_names, ne, name)
                ne.set_id(avg_names[ind].get_id())
                ne.set_related(avg_names[ind])
                avg_names[ind].set_related(ne)

        longest_names = [ne for ne in ne_person_names if ne.get_word_count() > 2]
        longest_string_names = [ne.get_lemma().split(' ')[-1] for ne in longest_names if
                                ne.get_word_count() > 2]

        for ne in short_names:
            name = ne.get_lemma()
            if name in longest_string_names:
                ind = self.find_most_relevant_index(longest_names, longest_string_names, ne, name)
                ne.set_id(longest_names[ind].get_id())
                ne.set_related(longest_names[ind])
                longest_names[ind].set_related(ne)

    def find_related_names(self, avg_names, avg_string_names, short_names):

        for ne in short_names:
            name = ne.get_lemma()
            if name in avg_string_names:
                ind = self.find_most_relevant_index(avg_names, avg_string_names, ne, name)
                ne.set_id(avg_names[ind].get_id())
                ne.set_related(avg_names[ind])
                avg_names[ind].set_related(ne)

    # Find indeces for mentions of a person from array
    def find_most_relevant_index(self, ne_target, target, current_ne, name):
        logger.info("[GROUPING] Process name %s (%s)", str(name), str(current_ne))

        # Construct dictionary of indeces and named entities (type: PersonName)
        # that are filtered based on named entity string and given person name string.
        indeces_d = {index: value for index, value in enumerate(target) if value == name}
        indeces_ne = {ne_target[index].get_id(): index for index, value in indeces_d.items()}
        indeces = list(indeces_d.keys())

        possible_nes = dict()
        logger.debug("[GROUPING] Indeces for name=%s: %s", str(name), str(indeces_d))

        # Loop through indeces of similar person names, e.g. Sauli Niinistö, Ville Niinistö
        for ind in indeces:
            # take named entity associated with the string
            n = ne_target[ind]

            # record it to a dictionary with index as a key and named entity as value
            if self.has_similar_entities(possible_nes, n) == False:
                possible_nes[n] = ind
            else:
                logger.debug("[GROUPING] Skipping %s, %s (Because: %s)", str(n), str(ind), str(possible_nes))

        # check if there are more than one option and disambiguate if reguired
        if len(possible_nes) > 1:
            logger.info("[GROUPING] More than one possible outcomes: %s", str(possible_nes.keys()))
            logger.info("[GROUPING] All: %s", str(possible_nes))
            related_count = self.get_related_counted(possible_nes)
            max_value = max(related_count.items(), key=lambda x: x[1])
            max_values = [indeces_ne[k.get_id()] for k, v in related_count.items() if v == max_value[1]]
            nes_max_values = [ne_target[k] for k in max_values]
            logger.debug("[GROUPING] Max values: %s || %s || %s", str(max_value), str(max_values), str(nes_max_values))
            if len(nes_max_values) > 1:
                # Get named entity that is closest
                ne_ind = self.get_closest_entity(nes_max_values, current_ne)

                if ne_ind in possible_nes:
                    logger.info("[GROUPING] Selected index: %s %s", str(ne_ind), str(possible_nes[ne_ind]))
                    return possible_nes[ne_ind]
                else:
                    logger.debug("[GROUPING] Selected index (keys): %s %s", str(ne_ind), str(possible_nes.keys()))
                    logger.debug("[GROUPING] Selected index (values): %s %s", str(ne_ind), str(possible_nes.values()))
                    for val in nes_max_values:
                        logger.debug("[GROUPING ERROR] from list %s key %s", nes_max_values, val)
                        logger.debug("[GROUPING ERROR] search for %s in ne indeces: %s", val.get_id(),
                                     indeces_ne)
                        if val.get_id() in indeces_ne:
                            return indeces_ne[val.get_id()]
                        return indeces_ne[nes_max_values[0].get_id()]

            else:
                logger.info("[GROUPING] Return ne_target: %s", indeces_ne[nes_max_values[0].get_id()])
                logger.info("[GROUPING] Return target: %s", nes_max_values[0])
                return indeces_ne[nes_max_values[0].get_id()]

        # if there is only one candidate
        elif len(possible_nes) == 1:

            ind = list(possible_nes.keys())[0]
            logger.info("[GROUPING] Return just one: %s", ind)
            logger.info("[GROUPING] Return ne_target: %s", possible_nes[ind])
            logger.info("[GROUPING] Return target: %s", possible_nes[ind])
            return possible_nes[ind]
        else:
            return None

        # Case: Ville Niinistö and Sauli Niinistö mentioned same amount
        #    if len(n.get_related_nes()) == len(current_ne.get_related_nes()):
        #        equals.append(n)
        # Case: Sauli Niinistö is mentioned more often than Ville Niinistö
        #    elif len(n.get_related_nes()) > len(current_ne.get_related_nes()):
        #        return ind
        # Case: Ville Niinistö is mentioned more often than Sauli Niinistö
        #    else:
        # return -1 # current

    def get_related_counted(self, entities):
        related = dict()
        for entity in entities:
            if entity not in list(related.keys()):
                related[entity] = set(entity.get_related())
            else:
                related[entity].union(entity.get_related())

        return related

    def has_similar_entities(self, entities, current):
        if current not in list(entities.keys()):
            return False
        else:
            for entity in entities:
                if current.get_lemma() == entity.get_lemma() and len(entity.get_lemma()) > 1:
                    return True
                else:
                    if current.get_string() == entity.get_string() and len(entity.get_string()) > 1:
                        return True
        return False

    # In case there are two persons referenced with same last name that are referenced equally in text,
    # check which reference is closer.
    def get_closest_entity(self, entities, current):
        options = dict()
        for entity in entities:
            related = entity.get_related()
            closest = dict()

            min_current = min(current.get_start_char_index())
            logger.debug("Min entity: %s > %s", str(min_current), min(entity.get_document_end_char_index()))

            if min(entity.get_document_end_char_index()) < min_current:
                closest[entity] = min(entity.get_document_end_char_index()) - min_current
            else:
                logger.debug("ELSE Min options: %s - %s", str(entity.get_document_end_char_index()), str(min_current))

            if len(related) > 0:
                for rel in related:
                    logger.debug("Min rel: %s %s", str(min_current), min(rel.get_document_end_char_index()))
                    if min(rel.get_document_end_char_index()) < min_current:
                        closest[rel] = rel.get_document_end_char_index() - min_current

            logger.debug("Min closest: %s (%s)", str(closest), str(current))
            if len(closest) > 0:
                # append the entity with the lowest value into the dictionary
                key_min = min(closest.keys(), key=(lambda k: closest[k]))
                options[entity] = closest[key_min]

            else:
                options[entity] = min_current

        key_min = min(options.keys(), key=(lambda k: options[k]))
        return key_min

    def render_entities_json(self, entities, context=0):
        results = list()
        ids = list()
        sorted_entities = entities

        if len(entities) > 1:
            try:
                sorted_entities = sorted(entities, key=lambda x: x.document_char_start_ind[0])
            except IndexError as inderr:
                for e in entities:
                    if len(e.document_char_start_ind) < 1:
                        logger.error(e)
                logger.error(inderr)
                logger.error(traceback.format_exc())
                sorted_entities = entities

        for entity in sorted_entities:
            hash, item = entity.render_json(context=context)
            if hash not in ids:
                ids.append(hash)
                results.append(item)
            else:
                logger.debug("Ignore: %s, %s, %s", hash, id, item)

        return results

    def __str__(self):
        return "Structure is " + str(self.id) + "=" + str(self.structures)
