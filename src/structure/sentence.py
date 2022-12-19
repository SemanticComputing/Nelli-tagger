import os, re
import logging, logging.config
from src.ner.nescore import NeScore

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('doc')


class Sentence:
    def __init__(self, start_char=None, end_char=None):
        self.uri = None
        self.words = dict()
        self.id = None
        self.next = None
        self.prev = None
        self.NEs = list()
        self.disambiguated = None
        self.sentence_string = ""
        self.sorted = False
        self.paragraph = None

        self.start_char_location = None
        self.set_start_char_location(start_char)

        self.end_char_location = None
        self.set_end_char_location(end_char)

    def get_document_start_char_location(self):
        return self.start_char_location

    def get_document_end_char_location(self):
        return self.end_char_location

    def set_start_char_location(self, start):
        if start is not None:
            self.start_char_location = start

    def set_end_char_location(self, end):
        if end is not None:
            self.end_char_location = end

    def set_sentence(self, sId, next, prev, words, uri, sen_str=""):
        self.uri = self.convert_to_sentence_uri(uri)
        self.id = int(sId)
        self.next = next
        self.prev = prev
        self.words = words
        self.sentence_string = sen_str
        self.set_word_indexes()

    def sort_nes(self):
        if not self.sorted:
            self.NEs = sorted(self.NEs, key=lambda x: -len(x.string))
            self.sorted = True

    def sort_nes_by_location(self, nes):
        if nes is not None:
            if len(nes) > 1:
                nes = sorted(nes, key=lambda x: -len(x.string))
                return sorted(nes, key=lambda x: x.start_char_ind)
        return nes

    def get_word_indexes(self):
        return set(self.words.keys())

    def get_disambiguated(self):
        return self.disambiguated

    def set_word_indexes(self):
        # get the right location of the first word in sentence
        first_word_id = list(self.words.keys())[0]
        first_word = self.words[first_word_id]
        start = self.sentence_string.find(first_word.get_word())
        end = 0
        prev_word = None
        prev_string = ""
        logger.info("Words: %s", self.words)
        for w, word in self.words.items():

            if prev_word is not None:
                prev_string = prev_word.get_word()
                next_char = prev_word.get_end_index()+1

            # case of punctuation
            if len(word.get_word()) == 1 and (word.get_word() in ['»','«','–','-',',',':',';','.','?',')','(','”','"', '[', ']'] or (word.get_word().isalpha() and word.get_word().islower() and prev_string in ['»','«','–','-',',',':',';','.','?',')','(', '[', ']','”'])):

                end = start + len(word.get_word()) -2

                logger.info("[WORD] CHECK: %s (%s, %s-%s)", word.get_word(), len(word.get_word()),
                            start, end)

                if start == self.sentence_string.find(first_word.get_word()) and end < 0:
                    if word.get_word() in ['–','-',',',':',';','.','?',')','(', '[', ']']:

                        end = start + len(word.get_word()) -1
                    else:
                        end = 0
                elif start > self.sentence_string.find(first_word.get_word()) and start > end and (word.get_word() == '–' or word.get_word() == '-' or word.get_word() == '"' or word.get_word() == '[' or word.get_word() == ']' or word.get_word() == '”'):
                    logger.info("[WORD] Probelm with ending (end_ind=%s, prev_end_ind=%s, word=%s)", prev_word.get_end_index(), end, word.get_word() )
                    end = start
                else:
                    if prev_word is not None:
                        logger.info("[WORD] Unidentified problem with ending (end_ind=%s, prev_end_ind=%s, word=%s)", prev_word.get_end_index(), end, word.get_word() )
                    else:
                        logger.info("[WORD] Unidentified problem with ending (end_ind=%s, word=%s)",
                                    end, word.get_word())

                start = end
                logger.info("[WORD] Special: %s (%s, %s-%s)", word.get_word(), len(word.get_word()),
                            start, end)
            # inflection related to ':' char
            elif prev_word is not None and prev_string in [':'] and self.sentence_string[end + 1] != " ":

                end = start + len(word.get_word()) - 2
                start = prev_word.get_end_index()+1
                logger.info("[WORD] Another special: %s (%s, %s-%s)", word.get_word(), len(word.get_word()),
                            start, end)
            # others
            else:
                end = start + len(word.get_word()) - 1
                logger.info("[WORD] Other: %s (%s, %s-%s)", word.get_word(), len(word.get_word()),
                            start, end)

            if start <= end:
                if self.sentence_string[start:end] == word.get_word():
                    word.set_start_index(start)
                    word.set_end_index(end)
                else:
                    # possibly more than one space somewhere in the text
                    logger.info("Reconfiguring location: %s, %s", self.sentence_string[start:end], word.get_word())
                    try:
                        possible_word_locations = [m.start() for m in re.finditer(re.escape(word.get_word()), self.sentence_string)]
                        closest = min(possible_word_locations, key=lambda x: abs(x - start))
                        if len(word.get_word())==1:
                            start = closest
                            end = start + len(word.get_word())
                        else:
                            start = closest
                            end = start + len(word.get_word())

                        logger.info("Resetting start and end, %s-%s", start, end)
                        if self.sentence_string[start:end] == word.get_word():
                            word.set_start_index(start)
                            word.set_end_index(end)
                        else:
                            logger.warning("Possibly dangerous location for a string: %s-%s, %s", start, end, self.sentence_string[start:end])
                            word.set_start_index(start)
                            word.set_end_index(end)
                    except Exception as err:
                        logger.warning("Failed to find location of %s in sentence %s, %s-%s", word.get_word(), self.sentence_string, start, end)
                        word.set_start_index(start)
                        word.set_end_index(end)
            else:
                logger.warning('problem with indexs %s %s', start, end)
                logger.warning('word index %s', word)

            if word.get_word() in ['”','"']:
                start = end + 1
            else:
                start = end + 2
            prev_word = word

    def get_ne_indexes(self):
        dct = dict()
        for ne in self.NEs:
            start = ne.get_start_ind()
            end = ne.get_end_ind()
            indexes = list()
            if type(start) == list and type(end) == list:
                starts = start
                ends = end
                for i, v in enumerate(starts):
                    start = starts[i]
                    end = ends[i]
                    inds = [x for x in range(start, end + 1)]
                    indexes.extend(inds)
            else:
                if end > start:
                    indexes = [x for x in range(start, end+1)]
                elif start == end:
                    indexes = [start, end]
            dct[ne] = set(indexes)
        return dct

    def find_word_ind(self, b):
        dtc = dict()
        logger.debug("Find indeces for %s from %s",b,self.words.values())
        keys = list(self.words.keys())
        indeces = list()
        a = [w.get_word() for w in list(self.words.values())]

        # create a list of indeces for a named entity
        indeces = [(i, i + (len(b)-1)) for i in range(len(a)) if a[i:i + len(b)] == b]

        logging.debug("For string %s find: %s from %s that is %s",str(b), str(indeces), str(keys), str(a))
        if len(indeces) < 1:
            return dtc

        t = indeces[0]

        logger.debug('Optional INdeces %s',indeces)

        dtc = {keys[t[0]]: keys[t[1]] for t in indeces}

        return dtc

    def ne_intersection(self):
        logger.debug("#################################################")
        logger.debug("[ne_intersection] %s",self.sentence_string)
        indexes = self.get_ne_indexes()
        dct = dict()
        intersection_cnt = 0
        for i in indexes:
            list_i = list()
            ind_i = indexes[i]
            for j in indexes:
                if i != j:
                    ind_j = indexes[j]

                    intersection = ind_i.intersection(ind_j)
                    values_list = []
                    for value in dct.values():
                        values_list = values_list + value
                    if len(intersection) > 0 and j not in dct.keys() and j not in values_list:
                        list_i.append(j)

                    if len(intersection) > 0:
                        intersection_cnt += 1

            if len(list_i) == 0 and intersection_cnt == 0:
                list_i.append(i)
            if len(list_i) > 0:
                if i not in list_i:
                    list_i.append(i)
                dct[i] = list_i
            intersection_cnt = 0
        return dct


    def ne_intersections_and_loners(self):
        indexes = self.get_ne_indexes()
        dct = dict()
        for i in indexes:
            list_i = list()
            ind_i = indexes[i]
            for j in indexes:
                if i != j:
                    ind_j = indexes[j]

                    intersection = ind_i.intersection(ind_j)
                    values_list = []
                    for value in dct.values():
                        values_list = values_list + value
                    if len(intersection) > 0 and j not in dct.keys() and j not in values_list:
                        list_i.append(j)
            if i not in list_i:
                list_i.append(i)
            if len(list_i) > 0:
                dct[i] = list_i

        return dct

    # calculate the longest NEs from lists of NEs that intersect, i.e. have been identified from the same are
    def find_longest_ne(self):
        indexes = self.get_ne_indexes()
        intersections = self.ne_intersection()

        longest_nes = dict()
        filtered_values = list()

        if len(intersections) > 0:
            for i in intersections:
                logger.debug("[LONGEST] Init max with %s",list(indexes[i]))
                max = len(indexes[i])
                max_ne = i
                a = intersections[i]

                # loop over intersecting NEs
                logger.debug("[LONGEST] Intersecting ne: %s ", a)
                for j in a:
                    l = len(indexes[j]) # get length of the term

                    # take the longest
                    if l > max and j not in list(longest_nes.values()) and j not in filtered_values and j not in longest_nes:
                        if j.get_total_score() >= max_ne.get_total_score():
                            if max_ne not in filtered_values:
                                filtered_values.append(max_ne)
                            max = l
                            max_ne = j
                        else:
                            filtered_values.append(j)
                    # if len is the same, then check the ne type and get ne type with higher score
                    elif l == max and j not in list(longest_nes.values()) and j not in filtered_values and j not in longest_nes:
                        if j.get_total_score() > max_ne.get_total_score(): #self.ne_priority[j.get_type()] > self.ne_priority[max_ne.get_type()]:
                            if max_ne not in filtered_values:
                                filtered_values.append(max_ne)
                            max = l
                            max_ne = j
                        else:
                            filtered_values.append(j)
                    else:
                        if j not in filtered_values:
                            filtered_values.append(j)
                if max_ne not in longest_nes and i not in longest_nes and i not in list(longest_nes.values()) and max_ne not in list(longest_nes.values()):

                    logger.debug("[LONGEST] Best score: %s, %s", max_ne, max_ne.get_score())
                    start = max_ne.get_start_ind()
                    end = max_ne.get_end_ind()
                    ind = str(start) + ":" + str(end)
                    longest_nes[ind] = max_ne

                    # Udpdate score: add 1 point for length
                    max_ne.add_score("longest",1)

        for i in indexes:
            max_ne = i
            if i not in intersections and i not in longest_nes and i not in filtered_values and i not in list(longest_nes.values()):

                start = max_ne.get_start_ind()
                end = max_ne.get_end_ind()
                ind = str(start) + ":" + str(end)
                longest_nes[ind] = max_ne

        return longest_nes


    def convert_to_sentence_uri(self, uri):
        return os.path.splitext(uri)[0]+".0"

    def get_uri(self):
        return self.uri

    def get_sentences(self):
        return self.senteces

    def get_html_identifier(self):
        return "s"+self.id

    def get_words(self):
        return self.words

    def get_sentence_string(self):
        return self.sentence_string

    def sentence_string(self):
        s= ""
        prev_upos = ''
        prev_word = ''
        for word in self.words:
            if len(s) > 0:
                logger.debug(word)

                s = s + " " + str(word.get_word())
            else:
                s = str(word.get_word())

        return s

    def set_ne(self, nes):
        self.NEs = nes

    def add_ne(self, ne):
        ne.set_sentence(self)
        if ne not in self.NEs:
            logger.debug('Adding ne %s to sentence %s', str(ne), str(self))
            self.NEs.append(ne)
        else:
            self.copy_ne(ne)

    def get_nes(self):
        return self.NEs

    def get_id(self):
        return self.id

    def get_word(self, ind):
        logger.debug("%s, %s", self.words, ind)
        if ind not in self.words:
            logger.info("[SENTENCE] get-word: ind=%s not in words: %s",str(ind), str(self.words))
        return self.words[ind]

    def set_paragraph(self, parag):
        self.paragraph = parag

    def set_word_feats(self, ind, form, lemma, upos, xpos, edge, head, deprel, deps, misc, feats):
        if ind in self.words:
            w = self.words[ind]
            if w.get_word().strip().lower() == form.strip().lower():
                w.set_feat(feats)
                w.set_upos(upos)
                w.set_lemma(lemma)
                w.set_xpos(xpos)
                w.set_head(head)
                w.set_edge(edge)
                w.set_deprel(deprel)
                w.set_deps(deps)
                w.set_misc(misc)
            elif w.get_word().strip().lower() != form.strip().lower() and ((upos == "NUM" or upos == "PUNCT") and form.strip().lower() in w.get_word().strip().lower()):
                logger.warning('[WARN] Case of broken descimal %s (%s)', w, form)
                return -1
            else:
                logger.warning('[WARN] Cannot identify %s (%s)', w, form)
                words = {w:w.get_word() for w in self.words.values()}
                decimal_check = False
                prev_upos = None
                for w, wordform in words.items():
                    if form == wordform and ind < w.get_id():
                        w.set_feat(feats)
                        w.set_upos(upos)
                        w.set_lemma(lemma)
                        w.set_xpos(xpos)
                        w.set_head(head)
                        w.set_edge(edge)
                        w.set_deprel(deprel)
                        w.set_deps(deps)
                        w.set_misc(misc)


        else:
            logger.warning("[WARN] %s with ind (%s) not in words (%s)", form, ind, self.words)
        return None

    def has_ne(self, ne):
        if ne in self.NEs:
            return True
        return False

    def get_ne(self, string):
        for ne in self.NEs:
            if ne.get_string() == string:
                return ne
        return None

    def copy_ne(self, cp_ne):
        for ne in self.NEs:
            if cp_ne == ne:
                for label, link in cp_ne.get_related_matches().items():
                    for l in link.split(','):
                        if l not in ne.get_links():
                            ne.add_related_match(label, l)

    def lemmatize_nes(self):
        for ne in self.NEs:
            ne.lemmatize()

    def list_words_between_indeces(self,start, end):
        words = list()
        if start == end:
            word = self.words[start]
            words.append(word)
        else:
            for index in range(start, end+1):
                if index in self.words:
                    word = self.words[index]
                    words.append(word)
                else:
                    logger.warning("Words: %s", self.words)
                    logger.warning("Cannot find index: %s", index)

        logger.debug("Entity %s contains words %s", words, self)
        return words

    def get_named_entities_at(self, start, end, string, type):
        for ne in self.NEs:
            if ne.get_end_ind() == end and ne.get_start_ind() == start:
                if ne.get_string() == string:
                    if ne.get_type() == type:
                        return ne
        return None

    def get_similar_named_entities_at(self, start, end, string, type):
        logger.info("[get_similar_named_entities_at] %s, %s ---------------------------------------------------------------", string, type)
        given_location_range = set(range(start, end+1))
        nes = NeScore()
        logger.info("Compare %s (%s) %s - %s", string, type, str(start), str(end))
        for ne in self.NEs:

            logger.info("With ne %s", ne)
            if ne.get_end_ind() == end and ne.get_start_ind() == start:
                logger.info("Location matches %s with %s,%s (%s)", ne, start, end, string)
                if ne.get_string() == string:
                    logger.info("String form matches")
                    if ne.get_type() == type:
                        logger.info("Same type %s with %s (%s)", ne, type, string)
                        return ne
                    elif ne.get_simple_type() == nes.get_ne_simple_type(type):
                        logger.info("Similar type %s with %s (%s)", ne, type, string)
                        return ne
                    else:
                        logger.info("Type doesn't match: %s, %s", ne.get_type(), type)
                else:
                    logger.info("String form doesn't match: %s != %s", ne.get_string(), string)
            # check if two named entities overlap based on location range
            else:
                logger.info("Location overlapping %s with %s,%s (%s)?", ne, start, end, string)
                ne_start = ne.get_start_ind()
                ne_end = ne.get_end_ind()
                if isinstance(ne_start, list) and isinstance(ne_end, list):
                    for s, e in zip(ne_start, ne_end):
                        comp_location_range = set(range(s,e+1))
                        comp = given_location_range.intersection(comp_location_range)
                        logger.info("Overlap results: %s, %s (%s/%s)", comp, len(comp), comp_location_range, given_location_range)
                        if len(comp) > 0:
                            if string in ne.get_string():
                                if ne.get_type() == type:
                                    logger.info("Same type %s with %s (%s)", ne, type, string)
                                    return ne
                                elif ne.get_simple_type() == nes.get_ne_simple_type(type):
                                    logger.info("Similar type %s with %s (%s)", ne, type, string)
                                    return ne
                else:
                    comp_location_range = set(range(ne_start, ne_end+1))
                    comp = given_location_range.intersection(comp_location_range)
                    logger.debug("Overlap results: %s, %s (%s/%s)", comp, len(comp), comp_location_range, given_location_range)
                    if len(comp) > 0:
                        if string in ne.get_string():
                            if ne.get_type() == type:
                                logger.info("Same type %s with %s (%s)", ne, type, string)
                                return ne
                            elif ne.get_simple_type() == nes.get_ne_simple_type(type):
                                logger.info("Similar type %s with %s (%s)", ne, type, string)
                                return ne

        return None

    def get_named_entity_string(self, start, end):
        ne = ""
        real_ne = ""
        words = list()

        if start == end:
            word = self.words[start]
            words.append(word)
            ne = "" + word.get_word()
            real_ne = ne
            return real_ne, words
        else:
            for i in range(start, end+1):
                if i in self.words:
                    word = self.words[i]
                    words.append(word)
                    if len(ne) == 0:
                        ne = "" + word.get_word()
                    elif len(ne) > 0:
                        ne = ne + " " + word.get_word()
                    else:
                        logger.warning("Error, NE len < 0")
            real_ne = self.sentence_string[words[0].get_start_index():words[-1].get_end_index()]
        logger.debug("get_named_entity_string: %s - %s (%s)", start, end, words)
        return real_ne, words

    def get_ne_groups(self):

        # apply scoring for the longest of each group
        self.find_longest_ne()

        # find groups
        ne_group = self.ne_intersection()
        ne_groups = dict()
        ne_group_primarys = dict()
        cnt = 1
        max_member=None

        # find primaries and list the top scoring ones
        for i in ne_group:
            # prepare
            ne_groups[cnt] = ne_group[i]
            max_score = 0
            max_member = None

            #get top score
            for member in ne_group[i]:
                if member.get_total_score() >= max_score:
                    max_score = member.get_total_score()
                    max_member = member

            # if there are multiple with same score, get longest option
            for member in ne_group[i]:
                if member.get_total_score() == max_score and len(member.get_string())>=len(max_member.get_string()):
                    max_member = member

            # append the top scoring to the list of primaries
            if cnt not in ne_group_primarys:
                ne_group_primarys[cnt] = list()
            ne_group_primarys[cnt].append(max_member)

            logger.debug("Group %s",ne_group[i])
            logger.debug("Disambiguated %s group %s", cnt, ne_group_primarys[cnt])

            cnt += 1

        return ne_group_primarys

    def get_disambiguated_nes(self, id):
        named_entities = list()

        if self.disambiguated is None:
            # get named entity group primaries

            # sort named entities by length from longest to shortest
            self.sort_nes()

            grouped_nes_primaries = self.get_ne_groups()

            if len(grouped_nes_primaries) > 0:
                for key, val in grouped_nes_primaries.items():
                    # get the longest string from list of string(s) of top scoring candidates
                    entity = self.get_longest_entity(val)
                    named_entities.append(entity)
            else:
                return self.NEs,id

            if self.disambiguated is None:
                named_entities = self.sort_nes_by_location(named_entities)
                self.disambiguated = named_entities
            else:
                logger.info("SKIPPING, resetting entiti ids")

            logger.debug("Returning NEs %s", named_entities)
            return named_entities,id

        else:
            return self.disambiguated, id

    def get_longest_entity(self, nes):
        strings = list()
        longest = None
        for ne in nes:
            if longest is not None:
                if len(ne.get_string()) > len(longest.get_string()):
                    longest = ne
            else:
                longest = ne
        return longest

    def resetentity_ids(self,entities,id=0):
        idmap = dict()
        for ne in entities:

            exists = self.check(ne, idmap.keys())
            if exists is not None:
                ne.set_id(idmap[exists])
                logger.debug("Copy id=%s for entity %s (%s)" % (idmap[exists], ne, id))
            else:
                ne.set_id(id)
                idmap[ne] = id
                id += 1

    def check(self, entity, key_list):
        for item in key_list:
            if item.get_string().lower().strip() == entity.get_string().lower().strip() or item.get_lemma().lower().strip() == entity.get_lemma().lower().strip():
                if item.get_type().lower().strip() == entity.get_type().lower().strip():
                    return item
                else:
                    return None
        return None

    def render_html(self, id, setup=None):
        logger.info("[RENDER HTML FOR SENTENCE]: %s", self.sentence_string)
        named_entities, id = self.get_disambiguated_nes(id)

        annotated = self.sentence_string
        counter = 1
        identifiers = dict()
        annotated_sentence = self.sentence_string
        identifier = "#" + str(counter)
        logger.info("----------------------------------------------------------------------------------------------------------")
        logger.info("Others %s", self.NEs)
        logger.info("PRIMARIEs %s", named_entities)
        for ne in named_entities:
            if ne.get_type() in setup['categories'] or len(setup['categories'])==0:
                annotated_ne = ne.render_html(setup=setup)
                starts = ne.get_start_char_index()
                ends = ne.get_end_char_index()
                if type(starts) == list and type(ends) == list:
                    for i, v in enumerate(starts):
                        start = starts[i]
                        end = ends[i]
                        buffer = len(ne.get_string())-1
                        logger.info('[ANNO] BUFFER: %s = %s - %s, (%s - %s = %s), %s',str(buffer), str(len(ne.get_string())), str(len(str(counter))), str(start), str(end), str(end-start), ne.get_string().strip())
                        if (len(ne.get_string())) > 2:
                            identifier = "#"+str(counter).zfill(buffer)
                        else:
                            identifier = "#" + str(counter)

                        if str(annotated_sentence[start:end]) == ne.get_string():
                            logger.info("[ANNO] Add annotation %s to %s-%s (replacing, %s, from, %s)", str(identifier), str(start), str(end), str(annotated_sentence[start:(end)]), annotated_sentence)
                            annotated_sentence = annotated_sentence[:start] + identifier + annotated_sentence[end:]
                            identifiers[identifier] = annotated_ne
                        else:
                            logger.error("[ERROR] Trying to annotate (%s, %s) already annotated sentence %s, at (%s, %s)", ne.get_string(),annotated_sentence[start:end], annotated_sentence,str(starts),str(ends))
                            logger.warning("[ERROR] Annotated sentence is already annotated...")
                else:
                    start = int(starts)
                    end = int(ends)
                    buffer = (len(ne.get_string())) - len(str(counter))

                    if (len(ne.get_string())) > 2:
                        identifier = "#" + str(counter).zfill(buffer)
                    else:
                        identifier = "#" + str(counter)
                    annotated_sentence = annotated_sentence[:start] + identifier + annotated_sentence[end + 1:]
                    identifiers[identifier] = annotated_ne
                counter += 1

        for i, annotation in identifiers.items():
            annotated_sentence = annotated_sentence.replace(i, annotation)

        return annotated_sentence, id

    def get_annotated_sentence(self, id, setup=None):
        if len(self.NEs) > 0:
            r,idx = self.render_html(id, setup=setup)
            return r,idx
        else:
            return self.sentence_string, id

    def get_json_nes(self, disambiguate=False, setup=None):
        entities = list()
        idmap = dict()
        nes=None
        if not disambiguate:
            for ne in self.NEs:
                entities.append(ne)
        else:
            if self.disambiguated is not None:
                nes = self.disambiguated
            else:
                # disambiguate named entities
                named_entities, id = self.get_disambiguated_nes(id=0)
                if named_entities is not None:
                    if len(named_entities) > 0:
                        self.disambiguated = self.sort_nes_by_location(named_entities)
                        nes = named_entities
                    else:
                        if self.NEs is not None:
                            nes = self.sort_nes_by_location(self.NEs)
                        else:
                            nes = self.NEs
                else:
                    if self.NEs is not None:
                        nes = self.sort_nes_by_location(self.NEs)
                    else:
                        nes = self.NEs
            if nes is not None:
                for ne in nes:
                    if ne.get_type() in setup['categories'] or len(setup['categories'])==0:
                        entities.append(ne)

        return entities

    def __repr__(self):
        s = ""
        for wId in self.words:
            word = self.words[wId]
            if len(s) > 0:
                s = s + " " + str(word.get_word()) + " (" + str(word.get_upos()) +", "+ str(word.get_feat()) +")"
            else:
                s = str(word.get_word()) + " (" + str(word.get_upos()) +", "+ str(word.get_feat()) +")"
        sentence = "Sentence instance "+ str(self.id) + "# : " + str(s)
        return sentence

    def __str__(self):
        s = "Sentence instance "+ str(self.id) + ": " + str(self.words)
        return s
