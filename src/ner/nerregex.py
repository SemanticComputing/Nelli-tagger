from src.ner.namedentity import NamedEntity
import logging, logging.config
import operator
import traceback

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('linfer')

class NerRegEx:
    def __init__(self):
        self.times=[]

    # loop sentences to add named entities
    def identify(self, input):
        for structure in input:
            paragraphs = structure.get_paragraphs()
            for pid in paragraphs:
                paragraph = paragraphs[pid]
                sentences = paragraph.get_sentences()
                for sid in sentences:
                    logger.debug("SENTENCEs %s", sentences)
                    logger.debug("SENTENCE %s %s", sid, str(sentences[sid]))
                    sentence = sentences[sid]
                    words = sentence.get_words()
                    self.find_nes(sentence, words, structure)

    def ne_possibly_related(self, nes, string, lemma, type):
        # finding all possible matches and taking the most frequent option if there are many
        possible_matches = dict()
        for ne in nes:
            if ne.get_type() in type:
                ne_start = ne.get_start_char_index()
                ne_end = ne.get_end_char_index()
                ne_string = ne.get_string()
                if (string in ne_string and ((len(string)*2)>len(ne_string))) or (lemma in ne_string and ((len(lemma)*2)>len(ne_string))) or (lemma in ne.get_lemma() and ((len(lemma)*2)>len(ne.get_lemma()))):

                    if ne not in possible_matches:
                        possible_matches[ne] = 1
                    else:
                        possible_matches[ne] += 1
                elif ("PersonName" in type and ne.get_type() == "PersonName") and ((string in ne_string) or (lemma in ne_string) or (lemma in ne.get_lemma())):
                    if ne not in possible_matches:
                        possible_matches[ne] = 1
                    else:
                        possible_matches[ne] += 1

        if len(possible_matches)>0:
            maksimi = max(possible_matches.items(), key=operator.itemgetter(1))[0]
            return maksimi
        return None

    def check_single_propn(self, input, n, start):
        counter = 0
        for i in range(start, len(input)):
            if i in input:
                n = input[i]
                if n.get_upos() == "PROPN":
                    counter += 1
                else:
                    if counter == 1:
                        return True
                    return False

    # find named entities from a sentence
    def find_nes(self, sentence, words,structure):
        nes = structure.get_named_entities_list()
        logger.info("%s",sentence)
        logger.info("%s", words)
        for ind in words:
            word = words[ind]
            w = word.get_word()

            upos = word.get_upos()
            logger.info("GOT: %s %s",w, upos)
            if upos == "PROPN":
                name, pattern_end = self.identify_names(words, ind)
                single = self.check_single_propn(words, word, ind)
                logger.info("Found name %s or single %s", name, single)
                if name:
                    ne = self.create_named_entity(ind, pattern_end, sentence, "PersonName", "Linguistic Rules", 1)
                    if sentence.has_ne(ne) == False:
                        sentence.add_ne(ne)
                        logger.info("Adding person ne %s (%s) for sentence %s", w, ne, sentence.get_sentence_string())

                    pattern_end = 0
                elif single:
                        pattern_end = ind
                        related = self.ne_possibly_related(nes, w, word.get_lemma(),["PersonName"])
                        if related != None:
                            ne = self.create_named_entity(ind, pattern_end, sentence, "PersonName", "Linguistic Rules",1,related=related)
                            if sentence.has_ne(ne) == False:
                                sentence.add_ne(ne)
                                logger.info("Adding person ne %s (%s) for sentence %s", w, ne,
                                            sentence.get_sentence_string())
                            pattern_end = 0
                            related.set_related(ne)
                        else:
                            single = False

                place, pattern_end = self.identify_places(words, ind)
                logger.info("Found place %s, %s-%s", place, ind, pattern_end)
                if place:
                    ne = self.create_named_entity(ind, pattern_end, sentence, "PlaceName", "Linguistic Rules", 1)
                    if sentence.has_ne(ne) == False:
                        sentence.add_ne(ne)
                        logger.info("Adding place ne %s (%s) for sentence %s", w, ne, sentence.get_sentence_string())
                    pattern_end = 0

                org, pattern_end = self.identify_organizations(words, ind)
                logger.info("Found ORG %s, %s", org, pattern_end)
                if org:
                    related = self.ne_possibly_related(nes, w, word.get_lemma(), ["CorporationName", "CorporationName", "SportsOrganizations","CultureOrganization","MediaOrganization"])
                    ne = self.create_named_entity(ind, pattern_end, sentence, "CorporationName", "Linguistic Rules", 1, related=related)
                    if sentence.has_ne(ne) == False:
                        sentence.add_ne(ne)
                        logger.info("[ORG] Adding organization ne %s (%s) for sentence %s", w, ne, sentence.get_sentence_string())
                    else:
                        logger.info("[ORG] NE in sentence already: %s, %s", ne, related)
                    pattern_end = 0

                # if not an organization, place, or a person, create anonym entities
                if org == False and place == False and name == False and single == False:
                    pattern_end = ind
                    ne = self.create_named_entity(ind, pattern_end, sentence, "AnonymEntity", "Linguistic Rules", 1)
                    if sentence.has_ne(ne) == False:
                        sentence.add_ne(ne)
                        logger.info("Adding unknown ne %s (%s) for sentence %s", w, ne, sentence.get_sentence_string())
                    pattern_end = 0
        sentence.lemmatize_nes()

    @staticmethod
    def create_named_entity(ind, pattern_end, sentence, ne_type, method, score, related=None):

        end = int(pattern_end)
        string, words = sentence.get_named_entity_string(ind, end)

        # add checkup for existing similar entity at same location
        ne = sentence.get_similar_named_entities_at(ind, end, string, ne_type)
        logger.info("NE Lookup %s", ne)
        if ne == None:
            # Add completely new named entity
            ne = NamedEntity()

            NerRegEx.set_ne(ind, method, ne, ne_type, pattern_end, sentence, string)
        else:
            # If there exists already same or similar entity...
            if ne.get_type() != ne_type:
                # ... but the type is different and still related to each other (e.g. PlaceName vs. GeographicalLocation)
                nes = ne
                nes.set_method(method, score)
                nes.set_simple_type_score()
                ne = NamedEntity()
                NerRegEx.set_ne(ind, method, ne, ne_type, pattern_end, sentence, string)
                ne.set_simple_type_score()
                if ne.get_string().strip() != string.strip() and ne.get_type() != ne_type:
                    ne.set_related(nes)
                    nes.set_related(ne)
            elif ne.get_string().strip() != string.strip() and ne.get_type() == ne_type:
                # ... but the string label is different and the type is the same (e.g. Sauli Väinämö Niinistö and Väinämä Niinistö)
                nes = ne
                nes.set_method(method, score)
                nes.set_simple_type_score()
                ne = NamedEntity()
                NerRegEx.set_ne(ind, method, ne, ne_type, pattern_end, sentence, string)
                ne.set_simple_type_score()
                ne.set_related(nes)
                nes.set_related(ne)

            else:
                # ... but it is the same entity, just update the existing
                end_word = sentence.get_word(pattern_end)
                start_word = sentence.get_word(ind)
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
                ne.set_simple_type_score()
        ne.set_method(method, score)

        if related != None:
            ne.set_related(related)

        return ne

    @staticmethod
    def set_ne(ind, method, ne, ne_type, pattern_end, sentence, string):
        try:
            if ind == pattern_end:
                ne.set_ne("", string, ind, pattern_end, ne_type, method)
                end_word = sentence.get_word(pattern_end)
                start_word = sentence.get_word(ind)
                ne.set_related_words(sentence.list_words_between_indeces(ind, pattern_end))
                ne.set_end_char_index(end_word.get_end_index())
                ne.set_start_char_index(start_word.get_start_index())
                ne.set_document_end_char_index(sentence.get_document_start_char_location() + start_word.get_start_index() + len(string))
                ne.set_document_start_char_index(sentence.get_document_start_char_location() + start_word.get_start_index())
                ne.set_case(end_word.get_case())
            else:
                ne.set_ne("", string, ind, pattern_end, ne_type, method)
                end_word = sentence.get_word(pattern_end)
                start_word = sentence.get_word(ind)
                ne.set_related_words(sentence.list_words_between_indeces(ind, pattern_end))
                ne.set_end_char_index(end_word.get_end_index())
                ne.set_start_char_index(start_word.get_start_index())
                ne.set_document_end_char_index(sentence.get_document_start_char_location() + start_word.get_start_index() + len(string))
                ne.set_document_start_char_index(sentence.get_document_start_char_location() + start_word.get_start_index())
                ne.set_case(end_word.get_case())
        except KeyError as kerr:
            if len(string.split(" ")) == 1:
                try:
                    start_word = sentence.get_word(ind)
                except Exception as err:
                    logger.warning("Unable to set NE (%s, %s,%s-%s):%s", (string, sentence, ind, pattern_end, str(err)))
                    logger.error(traceback.format_exc())
                    logger.warning("Unable to find word, delete entity:", str(ne))
                    del ne
                finally:
                    if start_word != None:
                        ne.set_related_words(sentence.list_words_between_indeces(ind, ind))
                        ne.set_end_char_index(start_word.get_end_index())
                        ne.set_start_char_index(start_word.get_start_index())
                        ne.set_document_end_char_index(
                            sentence.get_document_start_char_location() + start_word.get_start_index() + len(string))
                        ne.set_document_start_char_index(
                            sentence.get_document_start_char_location() + start_word.get_start_index())
                        ne.set_case(start_word.get_case())
                    else:
                        logger.warning("Unable to set NE (%s, %s,%s-%s):%s", (string, sentence, ind, pattern_end, str(kerr)))
                        logger.error(traceback.format_exc())
            else:
                logger.warning("Unable to set NE (%s, %s,%s-%s):%s", (string, sentence, ind, pattern_end, str(kerr)))
                logger.error(traceback.format_exc())
                logger.warning("Unable to find word, delete entity:", str(ne))
                del ne


    # identify names of people
    def identify_names(self, input, start):
        # Ida (PROPN, Case=Nom|Number=Sing) Aalberg (PROPN, Case=Nom|Number=Sing)
        # Ida (PROPN, Case=Nom|Number=Sing) Aalbergin (PROPN, Case=Gen|Number=Sing)
        name_edges = ["nmod:poss", "appos", "name", "nmod", "nmod:own"]

        #find pattern range
        start_ind = start + 1
        name = list()
        if start_ind < len(input):
            for i in range(start, len(input)):
                if i in input:
                    n = input[i]
                    logger.info("Identify names: %s %s %s %s", n.get_word(), n.get_upos(), n.get_deprel(), n.get_feat())
                    if n.get_upos() != "PROPN":
                        #after we are done with proper nouns
                        if self.check_organization_ending(n) == False:
                            return self.end_named_entity_search(i-1, name)
                        else:
                            return False, 0
                    else:
                        # checking if we have a propernouns in a healthy relationship with other words
                        feats = n.get_feat()
                        if (n.get_deprel() != "name" or n.get_deprel() == "") and len(name) == 0:
                            return False, 0
                        if feats.match("Ins","Plur") and len(name) == 0:
                            return False, 0
                        if n.get_word().startswith('<'):
                            return self.end_named_entity_search(i, name)
                        if n.get_word().endswith('>'):
                            return self.end_named_entity_search(i, name)
                        if feats.match("Abl","Sing"):
                            name.append(n)
                            return self.end_named_entity_search(i+1, name)
                        if feats.match("Nom","Sing") or n.get_deprel() == "name":
                            if self.check_organization_ending(n) == False:
                                name.append(n)
                            else:
                                return False, 0
                        elif feats.match("Gen", "Sing") and (n.get_deprel() in name_edges):
                            if self.check_organization_ending(n) == False:
                                name.append(n)
                            else:
                                return False, 0
                        elif feats.match("All", "Sing") and (n.get_deprel() in name_edges):
                            if self.check_organization_ending(n) == False:
                                name.append(n)
                            else:
                                return False, 0
                        elif feats.match("Ade", "Sing") and (n.get_deprel() in name_edges):
                            if self.check_organization_ending(n) == False:
                                name.append(n)
                            else:
                                return False, 0
        else:
            return False, 0

        return False, 0

    # identify names of places
    def identify_places(self, input, start):
        # Janakkalan (PROPN, Case=Gen|Number=Sing) Leppäkosken (UNKNOWN, UNKNOWN) Sipilän (PROPN, Case=Gen|Number=Sing)
        # talossa (NOUN, Case=Ine|Number=Sing)
        # Tukholman (PROPN, Case=Gen|Number=Sing) Kuninkaallisessa (ADJ, Case=Ine|Degree=Pos|Number=Sing) teatterissa

        place_edges = ["nmod:poss", "nommod", "nsubj-cop", "poss", "nsubj", "dobj", "nmod", "conj", "appos", "place"]
        noun_edges = ["nmod:poss"]
        bad_noun_edges = ["nmod:poss"]

        # find pattern range
        start_ind = start + 1
        name = list()
        prev_upos = None
        if start_ind <= len(input):
            for i in range(start, len(input)+1):
                if i in input:
                    n = input[i]
                    logger.info("Proccessing now [%s: %s, %s, %s]", str(n.get_word()), str(n.get_upos()), str(n.get_deprel()), str(n.get_feat()))
                    if n.get_upos() != "PROPN" and n.get_upos() != "NOUN" and prev_upos == "PROPN":
                        # after we are done with proper nouns and nouns
                        return self.end_named_entity_search(i-1, name)
                    if n.get_upos() != "PROPN" and n.get_upos() != "NOUN" and prev_upos == "NOUN":
                        # after we are done with proper nouns and nouns
                        return self.end_named_entity_search(i-1, name)
                    elif n.get_upos() == "NOUN":
                        prev_upos="NOUN"
                        feats = n.get_feat()

                        if n.get_word().startswith('<'):
                            return self.end_named_entity_search(i, name)
                        if n.get_word().endswith('>'):
                            return self.end_named_entity_search(i, name)
                        if feats.match("Ela", "Sing")==True and len(name) > 0:
                            return True, i # return previous index
                        elif feats.match("Ela", "Sing")==True and len(name) == 0:
                            return False, 0
                        elif self.check_organization_ending(n)==True and len(name)>0:
                            return False, 0
                        elif feats.match("Ade", "Sing")==True and n.is_first_letter_uppercase() == False:
                            return False, 0
                        elif n.get_edge() in bad_noun_edges and n.is_first_letter_uppercase() == False:
                            return self.end_named_entity_search(i, name)
                        elif feats.match("Com", "")==True and n.is_first_letter_uppercase() == False:
                            return self.end_named_entity_search(i, name)
                        elif feats.match("Com","Plur")==True and n.is_first_letter_uppercase() == False:
                            return False, 0
                        elif feats.match("Nom","Plur") and n.is_first_letter_uppercase() == False:
                            return self.end_named_entity_search(i, name)
                        elif feats.match("Nom","Sing") and n.is_first_letter_uppercase() == False and not(n.get_word().endswith('-')):
                            return self.end_named_entity_search(i, name)
                        elif feats.match("Nom", "Sing") and n.is_first_letter_uppercase() == False and n.get_word().endswith('-'):
                            return self.end_named_entity_search(i-1, name)
                        elif feats.match("Ess","Plur") and n.is_first_letter_uppercase() == False:
                            return self.end_named_entity_search(i, name)
                        elif feats.match("Ess","Sing") and n.is_first_letter_uppercase() == False:
                            return self.end_named_entity_search(i, name)
                        elif feats.match("Tra","Sing") and n.is_first_letter_uppercase() == False:
                            return self.end_named_entity_search(i, name)
                        elif feats.match("Gen", "Sing") and n.get_deprel() in place_edges:
                            return self.end_named_entity_search(i, name)
                        # checking if word is possessed by previous word
                        p = i #-1
                        if p > start_ind:
                            if n.get_edge() in noun_edges:
                                return True, i-1
                        else:
                            return False, 0
                    elif n.get_upos() == "PROPN":
                        # checking if we have a propernouns in correct case
                        prev_upos = "PROPN"
                        feats = n.get_feat()


                        if n.get_deprel() == "name":
                            return False, 0
                        elif n.get_word().isupper():
                            return False, 0
                        if feats.match("Nom", "Sing") and feats.get_derivation() == "" and n.get_deprel() in place_edges:
                            name.append(n)
                        elif feats.match("Gen", "Sing") and feats.get_derivation() == "" and n.get_deprel() in place_edges:
                            name.append(n)
                        elif feats.match("Ine", "Sing") and feats.get_derivation() == "" and (n.get_deprel() in place_edges or n.get_deprel() == ""):
                            name.append(n)
                        elif feats.match("Ill", "Sing") and feats.get_derivation() == "" and (n.get_deprel() in place_edges or n.get_deprel() == ""):
                            name.append(n)
                        elif feats.match("Abl","Sing"):
                            name.append(n)
                            return self.end_named_entity_search(i+1, name)
                        elif feats.match("Ade","Sing"):
                            name.append(n)

                            return self.end_named_entity_search(i, name)
                    elif n.get_upos() == 'PUNCT':
                        return self.end_named_entity_search(i-1, name)
                    else:
                        return self.end_named_entity_search(i, name)

        else:
            logger.info("End to identification: %s %s", str(input), str(start))
            return False, 0

        return self.end_named_entity_search(i, name)

    def check_organization_ending(self, n):
        logger.info("Check organization endings %s (%s, %s)", n, n.get_word(), n.get_lemma())
        endings = ["oy", "a/s", "ltd", "ky", "ay", "osk", "oyj", "ry", "rs", "rf"]
        public_domain = ["unioni", "puolue", "hallitus", "keskussairaala", "sairaala", "tutkimuskeskus", "keskuspankki", "laitos",
                   "pankki", "kirjasto", "vankila", "poliisi", "korkeakoulu", "yliopisto", "ammattioppilaitos", "ammattikoulu",
                   "koulu", "lyseo", "museo", "instituutti", "arkisto", "teatteri", "ooppera", "kansallisooppera", "kansallisteatteri",
                         "yläaste", "ala-aste", "kansakoulu", "yläkoulu", "alakoulu", "hallinto-oikeus", "käräjäoikeus", "raastuvanoikeus"
                         "korkeinoikeus", "hovioikeus", "virasto", "keskus", "valiokunta", "kunta", "eduskunta", "rahasto", "konttori", "rajavartiosto",
                         "poliisilaitos", "syyttäjänvirasto", "toimisto", "uutinen", "uutiset", "sanomat", "lehti", "kaupunkiuutiset", "kunnallissanomat",
                         "asunto", "asuntola", "asuntoyhtiö", "yhtiö", "seura", "yhteisö", "yhdistys", "säätiö", "liitto", "osasto", "reservi", "liike",
                         "ammattiliitto", "kaupunginvaltuusto", "neuvosto", "keskusjärjestö", "ylioppilaskunta", "kilta", "yhteiskoulu", "group", "komitea",
                         "komissio", "tuomioistuin", "hallinto", "parlamentti", "ritarikunta", "kustannus"]

        if len(n.get_word().split(' ')) > 1:
            if n.get_word().lower().strip() in endings or n.get_lemma().lower().strip() in endings:
                logger.info("YES 1: organization endings %s (%s, %s)", n, n.get_word(), n.get_lemma())
                return True
            else:
                if n.get_word().lower().strip() in public_domain or n.get_lemma().lower().strip() in public_domain:
                    logger.info("YES 2: organization endings %s (%s, %s)", n, n.get_word(), n.get_lemma())
                    return True
        elif len(n.get_word().split(' ')) == 1 and "-" in n.get_word():
            end = n.get_word().split('-')[-1]
            lemma_end = ""
            if len(n.get_lemma()) > 1:
                lemma_end = n.get_lemma().split('-')[-1]
            if end.lower().strip() in endings or lemma_end.lower().strip() in endings:
                logger.info("Contains organization endings %s (%s, %s)", n, n.get_word(), n.get_lemma())
                return True
            else:
                logger.info("NO: organization endings %s (%s, %s)", n, n.get_word(), n.get_lemma())
                if end.lower().strip() in public_domain or lemma_end.lower().strip() in public_domain:
                    logger.info("YES 3: organization endings %s (%s, %s)", n, n.get_word(), n.get_lemma())
                    return True
        else: # one word?
            if n.get_word().lower().strip() in public_domain or n.get_lemma().lower().strip() in public_domain:
                logger.info("YES 4: organization endings %s (%s, %s)", n, n.get_word(), n.get_lemma())
                return True

        return False

    # identify names of organizations
    def identify_organizations(self, input, start):
        # Ida (PROPN, Case=Nom|Number=Sing) Aalberg (PROPN, Case=Nom|Number=Sing)
        # Ida (PROPN, Case=Nom|Number=Sing) Aalbergin (PROPN, Case=Gen|Number=Sing)
        name_edges = ["nmod:poss", "appos", "name", "nmod"]

        # find pattern range
        start_ind = start + 1
        name = list()
        prev_entity = None
        if start_ind < len(input):
            for i in range(start, len(input)):
                if i in input:
                    n = input[i]
                    logger.info("WORD=%s UPOS=%s DEPREL=%s END=%s LEN=%s", n.get_word(), n.get_upos(), n.get_deprel(), str(self.check_organization_ending(n)), str(len(name)))
                    if (n.get_upos() == "NOUN" or n.get_upos() == "PROPN") and self.check_organization_ending(n)==True and len(name)>0:
                        # a company or organization name
                        name.append(n)
                        return self.end_named_entity_search(i, name, "CorporationName")
                    elif n.get_upos() == "PUNCT" and self.check_organization_ending(n)==False and len(name)>0:
                        return self.end_named_entity_search(i-1, name, "CorporationName")
                    elif n.get_upos() != "NOUN" and n.get_upos() != "PROPN":
                        # if the name doesn't end with accepted endings, ignore
                        if prev_entity.get_word().isupper() and prev_entity.get_feat().match("Nom", "Sing"):
                            return self.end_named_entity_search(i, name, "CorporationName")
                        elif n.is_first_letter_uppercase() == True and n.get_upos() == "ADJ" and n.get_deprel() == "amod":
                            name.append(n)
                        else:
                            return False, 0
                    elif n.get_upos() == "PROPN":
                        # checking if we have a propernouns in a healthy relationship with other words
                        feats = n.get_feat()
                        if n.get_deprel() == "":
                            return False, 0
                        if n.get_word().startswith('<'):
                            return self.end_named_entity_search(i, name, "CorporationName")
                        if n.get_word().endswith('>'):
                            return self.end_named_entity_search(i, name, "CorporationName")
                        if feats.match("Nom", "Sing") or n.get_deprel() == "name":
                            name.append(n)
                        elif feats.match("Gen", "Sing") and (n.get_deprel() in name_edges):
                            name.append(n)
                        elif feats.match("All", "Sing") and (n.get_deprel() in name_edges):
                            name.append(n)
                        elif n.get_word().isupper() and feats.match("Nom", "Sing"):
                            name.append(n)
                    else:
                        # false positive, ignore
                        return False, 0
                    prev_entity = n
        else:
            return False, 0

        return False, 0


    def end_named_entity_search(self,i, name, type=""):
        logger.info("Ending entity:%s, %s ", str(name), str(i))
        if len(name) == 0:
            return False, 0
        else:
            first = name[0]
            last = name[-1]
            if first.get_deprel() == "name" and self.check_organization_ending(last) == False and type == "CorporationName":
                return False, 0
            return True, i  # return previous index

    def identify_numbers(self, input):
        pass

    def identify_time(self, input):
        pass