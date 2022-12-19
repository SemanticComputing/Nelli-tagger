from src.ner.nescore import NeScore
import logging, logging.config
from src.ner.las_query import lasQuery
import hashlib, os
import validators
from validators import ValidationFailure
import re
from collections import OrderedDict

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('ne')


class NamedEntity:
    def __init__(self):
        self.uri = ""
        self.string = ""
        self.start_ind = 0
        self.end_ind = 0
        self.start_char_ind = list()
        self.end_char_ind = list()
        self.ne_type = None
        self.method = list()
        self.score = NeScore()
        self.relatedMatches = OrderedDict()
        self.relatedLinks = list()
        self.id = 0
        self.related_words = list()
        self.related_nes = list()
        self.lemma = ""
        self.case = ""
        self.las = lasQuery()
        self.word_length = 0
        self.sentence_location_start = 0
        self.sentence_location_end = 0
        self.document_char_start_ind = list()
        self.document_char_end_ind = list()
        self.alt_label = ""
        self.order_of_appearance = 0
        self.hash = None
        self.get_hash()
        self.sentence = None

        # ne context attributes
        self.c_gender = ""
        self.c_titles = ""
        self.c_dates = ""

    def set_ne(self, uri, string, start, end, type, method, score=None, id=0, lemma="", related=list(),
               start_char_ind=None, end_char_ind=None, titles="", gender="", date=""):

        if score != None:
            self.score = score

        self.uri = uri
        self.string = string
        self.start_ind = start
        self.end_ind = end
        self.set_type(type)

        if start_char_ind != None:
            self.set_start_char_index(start_char_ind)

        if end_char_ind != None:
            self.set_end_char_index(end_char_ind)

        if method not in self.method:
            self.method.append(method)
            self.add_score("method", 1)
        self.id = id
        if len(lemma) > 0:
            self.set_lemma(lemma)
        else:
            self.lemma = ""
        self.word_length = len(string.split(' '))

        if len(related) > 0:
            for link in related:
                self.add_related_match(lemma, link)

        # context for ne
        if titles:
            self.c_titles = titles

        if gender:
            self.c_gender = gender

        if date:
            self.c_dates = date

    # Getters
    def get_id(self):
        return self.id

    def get_word_count(self):
        return self.word_length

    def get_case(self):
        return self.case

    def get_lemma(self):
        return self.lemma.replace('#', '')

    def get_lemma_with_compound_separator(self):
        return self.lemma

    def get_related(self):
        return self.related_nes

    def get_method(self):
        return self.method

    def get_score(self):
        return self.score

    def get_uri(self):
        return self.uri

    def get_type(self):
        return self.ne_type

    def get_string(self):
        return self.string

    def get_start_ind(self):
        return self.start_ind

    def get_end_ind(self):
        return self.end_ind

    def get_total_score(self):
        return self.score.total_score()

    def get_related_matches(self):
        return self.relatedMatches

    def get_related_links(self):
        return self.relatedLinks

    def get_start_char_index(self):
        return self.start_char_ind

    def get_end_char_index(self):
        return self.end_char_ind

    def get_related_words(self):
        return self.related_words

    def get_sentence_start_idx(self):
        return self.sentence_location_start

    def get_sentence_end_idx(self):
        return self.sentence_location_end

    def get_alt_label(self):
        return self.alt_label

    def get_simple_type(self):
        return self.score.get_ne_simple_type(self.ne_type)

    def get_gender(self):
        return self.c_gender

    def get_titles(self):
        return self.c_titles

    def get_dates(self):
        return self.c_dates

    def get_number(self):
        if len(self.related_words) > 0:
            last_word = self.related_words[-1]
            return last_word.get_number()
        return None

    def get_document_start_char_index(self):
        return self.document_char_start_ind

    def get_document_end_char_index(self):
        return self.document_char_end_ind

    def is_plural(self):
        num = self.get_number()
        if num == 'Sing':
            return False
        elif num == 'Plur':
            return True
        return False

    # Setters
    def set_case(self, case):
        self.case = case

    def add_alt_label(self, label):
        self.alt_label = label

    def add_related_links(self, link):
        if link not in self.relatedLinks:
            self.relatedLinks.append(link)

    def set_lemma(self, lemma):
        logger.info("Set namedentity (%s) lemma to %s", self.string, self.lemma)
        if len(lemma) > 0 and len(self.string) > 0:
            lemma = lemma.replace("#", "")
            if self.ne_type in ["PersonName", "AnimalPerson", "MythicalPerson", "Product", "CorporationName",
                                "OrganizationName"]:
                self.lemma = lemma[:1].upper() + lemma[1:]
            elif self.string[0].isupper() == True and lemma[0].isupper() == False:
                self.lemma = lemma.capitalize()
            else:
                self.lemma = lemma

    def set_related(self, related):
        if related not in self.related_nes:
            self.related_nes.append(related)

    def set_type(self, type_uri):
        uri = type_uri.split("/")
        self.ne_type = uri[(len(uri) - 1)]
        # set score for type
        self.score.set_type_score(self.ne_type)

    def set_start_ind(self, ind):
        self.start_ind = ind

    def set_end_ind(self, ind):
        self.end_ind = ind

    def set_method(self, method, score=0):
        if method not in self.method:
            self.method.append(method)
            self.add_score("method", score)

    def set_score(self, score):
        self.score = score

    def set_sentence(self, sent):
        self.sentence = sent

    def set_start_char_index(self, ind):
        if ind not in self.start_char_ind:
            self.start_char_ind.append(ind)

    def set_end_char_index(self, ind):
        if ind not in self.end_char_ind:
            self.end_char_ind.append(ind)

    def set_document_start_char_index(self, ind):
        if ind not in self.document_char_start_ind:
            self.document_char_start_ind.append(ind)

    def set_document_end_char_index(self, ind):
        if ind not in self.document_char_end_ind:
            self.document_char_end_ind.append(ind)

    def set_simple_type_score(self):
        self.score.add_simple_type_score(self.ne_type)

    def set_related_words(self, words):
        if len(words) > 0:
            self.related_words = words
            self.sentence_location_end = words[-1].get_id()
            self.sentence_location_start = words[0].get_id()

    def set_id(self, ind):
        self.id = ind

    def set_related_match(self, related):
        if related != None:
            for label, link in related.items():
                self.add_related_match(label, link)

    def set_gender(self, gender):
        if len(gender) > 0:
            self.c_gender = gender

    def set_dates(self, dates):
        if len(dates) > 0:
            self.c_dates = dates

    def set_titles(self, titles):
        if len(titles) > 0:
            self.c_titles = titles

    def add_related_match(self, label, link):
        try:
            if validators.url(str(link)):
                if label.lower() not in self.relatedMatches.keys() and len(link) > 0:
                    self.relatedMatches[label.lower()] = link
                    self.add_score("link", 1)
                elif label.lower() in self.relatedMatches.keys() and len(link) > 0 and link not in list(
                        self.relatedMatches[label.lower()].split(',')):
                    self.relatedMatches[label.lower()] += ',' + str(link)
                else:
                    logger.warning("Cannot add link: %s", str(link))
                    logger.warning("label: %s relatedMatches: %s, %s", str(label.lower()),
                                   str(self.relatedMatches.keys()), str(self.relatedMatches.values()))
            else:
                logger.warning("Link is not valid: %s", link)
        except ValidationFailure as vf_err:
            logger.warning("Invalid URL %s", link)
        except Exception as err:
            logger.warning("Invalid URL %s", link)

    def add_score(self, metric, score):
        if metric == "longest":
            self.score.set_longest(score)
        elif metric == "type":
            self.score.set_ne_type(score)
        elif metric == "method":
            oldscore = self.score.get_method()
            self.score.set_method(score + oldscore)
        elif metric == "link":
            self.score.set_link(score)
        else:
            logger.warning("Unknown metric: ", metric)

    def add_related_word(self, word):
        if word not in self.related_words:
            self.related_words.append(word)
            self.sentence_location_end = self.related_words[-1].get_id()
            self.sentence_location_start = self.related_words[0].get_id()

    def get_links(self, filter=None):
        if filter != None:
            linklist = [link for link in self.relatedMatches.values() if filter not in link]
            return ",".join(linklist)
        links = ",".join(set(self.relatedMatches.values()))
        return links

    def get_hash(self):
        if self.hash == None:
            self.hash = hashlib.md5(os.urandom(32)).hexdigest()  # hash_object.hexdigest()
        return self.hash

    def query_lemma(self):
        res = self.las.lexical_analysis(self.string, "fi")
        return res

    def lemmatize(self):
        logger.info("CHECK LEMMA for %s", self.string)
        skipped = ["PUNCT", "NUM"]
        if self.lemma == self.string or len(self.lemma) == 0:
            lemma = self.string
            if len(self.related_words) < 1:
                logger.warning("Unable to lemmatize, no words %s for entity %s", self.related_words, self)
            else:
                ne_last_word = self.related_words[-1]
                features = ne_last_word.get_feat()
                if ne_last_word.get_upos() not in skipped:
                    if features.get_case().lower() != "nom":
                        if len(ne_last_word.get_lemma()) > 0 and ne_last_word.get_word() != ne_last_word.get_lemma():
                            lemma = lemma.replace(ne_last_word.get_word(), ne_last_word.get_lemma())
                        else:
                            if re.search('[a-zäöåA-ZÄÖÅ]', self.string):
                                logger.warning("Query lemma (lemma=%s) for ne_last_word=%s", ne_last_word.get_lemma(),
                                               ne_last_word.get_word())
                                lemma = self.query_lemma()
                            else:
                                lemma = self.string
                    else:
                        logger.info("Problem with case: " + str(ne_last_word))
                        lemma = self.string
                else:
                    pos = [p for p in self.related_words if p.get_upos() not in skipped]
                    if len(pos) > 0 and re.search('[a-zäöåA-ZÄÖÅ]', self.string):
                        lemma = self.query_lemma()
                    else:
                        lemma = self.string

                self.set_case(features.get_case())
            self.set_lemma(lemma)
        else:
            logger.info("Lemma may already exist for %s and %s, but checking case %s", self.string, self.lemma,
                        self.case)
            if len(self.case) < 1:
                if len(self.related_words) < 1:
                    logger.warning("Unable to lemmatize, no words %s for entity %s", self.related_words, self)
                else:
                    ne_last_word = self.related_words[-1]
                    features = ne_last_word.get_feat()
                    self.set_case(features.get_case())

    def lemmatize_related(self):
        if len(self.related_nes) > 0:
            for related in self.related_nes:
                related.lemmatize()

    def render_html(self, setup=None):
        html = ""
        if len(self.relatedMatches) > 0:
            if setup != None:
                if 'linking' in setup:
                    if setup['linking'] == 1 and len(self.relatedMatches) == 1:
                        links = self.get_links().split(',')
                        if 'modified' in setup and setup['modified'] > 0:
                            if len(links) > 1:
                                return "<span name='namedentity' data-entity-id=" + str(self.id) + \
                                       " data-occurrence-id='" + str(self.get_hash()) + \
                                       "' data-category='" + str(self.ne_type) + \
                                       "' data-case=\"" + str(self.case) + \
                                       "\" data-lemma=\"" + str(self.lemma.strip()) + \
                                       "\" data-link=\"" + str(self.get_links(filter="wikipedia")) + \
                                       "\" data-location=\"" + str(self.get_sentence_start_idx()) + "\"> " + \
                                       "<a id='a_id_" + str(self.get_hash()) + \
                                       "' tabindex='0' title='" + str(self.lemma.strip()) + \
                                       "' role='button' data-toggle='clickover' data-placement='bottom' " + \
                                       "data-links=" + str(self.get_links(filter="wikipedia")) + ">" + str(
                                    self.string.strip()) + "</a></span>"
                            else:
                                return "<span name='namedentity' data-entity-id=" + str(self.id) + \
                                       " data-occurrence-id='" + str(self.get_hash()) + \
                                       "' data-category='" + str(self.ne_type) + \
                                       "' data-case=\"" + str(self.case) + \
                                       "\" data-lemma=\"" + str(self.lemma.strip()) + \
                                       "\" data-link=\"" + str(self.get_links(filter="wikipedia")) + \
                                       "\" data-location=\"" + str(self.get_sentence_start_idx()) + "\"> " + \
                                       "<a id='a_id_" + str(self.get_hash()) + "' tabindex='0' title='" + str(
                                    self.lemma.strip()) + \
                                       "' role='button' data-toggle='clickover' data-placement='bottom' " + \
                                       "data-links=" + str(self.get_links(filter="wikipedia")) + ">" + str(
                                    self.string.strip()) + "</a></span>"
                        else:
                            html = "<span name='namedentity' data-entity-id='" + str(self.id) + \
                                   "' data-occurrence-id='" + str(self.get_hash()) + \
                                   "' data-category='" + str(self.ne_type) + \
                                   "' data-case='" + str(self.case) + \
                                   "' data-lemma='" + str(self.lemma.strip()) + \
                                   "' data-link='" + str(self.get_links(filter="wikipedia")) + \
                                   "' data-location='" + str(self.get_sentence_start_idx()) + "'>" + str(
                                self.string.strip()) + "</span>"
                    else:
                        html = "<span name='namedentity' data-entity-id='" + str(self.id) + \
                               "' data-occurrence-id='" + str(self.get_hash()) + \
                               "' data-category='" + str(self.ne_type) + \
                               "' data-case='" + str(self.case) + \
                               "' data-lemma='" + str(self.lemma.strip()) + \
                               "' data-location='" + str(self.get_sentence_start_idx()) + "'>" + str(
                            self.string.strip()) + "</span>"
                elif 'modified' in setup:
                    if setup['modified'] > 0:
                        html = "<span name='namedentity' data-entity-id='" + str(self.id) + \
                               "' data-occurrence-id='" + str(self.get_hash()) + \
                               "' data-category='" + str(self.ne_type) + \
                               "' data-case='" + str(self.case) + \
                               "' data-lemma='" + str(self.lemma.strip()) + \
                               "' data-link='" + str(self.get_links(filter="wikipedia")) + \
                               "' data-location='" + str(self.get_sentence_start_idx()) + "'>" + \
                               "<a class='a-click-toggle' id='a_id_" + str(self.get_hash()) + \
                               "' tabindex='0' title='" + str(self.lemma.strip()) + \
                               "' role='button' data-toggle='clickover' data-placement='bottom' " + \
                               "data-links='" + str(self.get_links(filter="wikipedia")) + "'>" + str(
                            self.string.strip()) + str(self.render_links_to_html(display=0)) + "</a></span>"
                    else:
                        html = "<span name='namedentity' data-entity-id='" + str(self.id) + \
                               "' data-occurrence-id='" + str(self.get_hash()) + \
                               "' data-category='" + str(self.ne_type) + \
                               "' data-case='" + str(self.case) + \
                               "' data-lemma='" + str(self.lemma.strip()) + \
                               "' data-link='" + str(self.get_links(filter="wikipedia")) + \
                               "' data-location='" + str(self.get_sentence_start_idx()) + "'>" + str(
                            self.string.strip()) + "</span>"
                else:
                    html = "<span name='namedentity' data-entity-id='" + str(self.id) + \
                           "' data-occurrence-id='" + str(self.get_hash()) + \
                           "' data-category='" + str(self.ne_type) + \
                           "' data-case='" + str(self.case) + \
                           "' data-lemma='" + str(self.lemma.strip()) + \
                           "' data-link='" + str(self.get_links(filter="wikipedia")) + \
                           "' data-location='" + str(self.get_sentence_start_idx()) + "'>" + str(
                        self.string.strip()) + "</span>"

            logger.info("Return html=%s", html)
            return html
        else:
            if 'modified' in setup:
                if setup['modified'] > 0:
                    html = "<span name='namedentity' data-entity-id='" + str(self.id) + \
                           "' data-occurrence-id='" + str(self.get_hash()) + \
                           "' data-category='" + str(self.ne_type) + \
                           "' data-case='" + str(self.case) + \
                           "' data-lemma='" + str(self.lemma.strip()) + \
                           "' data-link='" + str(self.get_links(filter="wikipedia")) + \
                           "' data-location='" + str(self.get_sentence_start_idx()) + "'>" + \
                           "<a class='a-click-toggle' id='a_id_" + str(self.get_hash()) + \
                           "' tabindex='0' title='" + str(self.lemma.strip()) + \
                           "' role='button' data-toggle='clickover' data-placement='bottom' " + \
                           "data-links='" + str(self.get_links(filter="wikipedia")) + "'>" + \
                           str(self.string.strip()) + str(self.render_links_to_html(display=0)) + "</a>" + "</span>"
                else:
                    html = "<span name='namedentity' data-entity-id='" + str(self.id) + \
                           "' data-occurrence-id='" + str(self.get_hash()) + \
                           "' data-category='" + str(self.ne_type) + \
                           "' data-case='" + str(self.case) + \
                           "' data-lemma='" + str(self.lemma.strip()) + \
                           "' data-link='" + str(self.get_links(filter="wikipedia")) + \
                           "' data-location='" + str(self.get_sentence_start_idx()) + "'>" + str(
                        self.string.strip()) + "</span>"
            else:
                html = "<span name='namedentity' data-entity-id='" + str(self.id) + \
                       "' data-occurrence-id='" + str(self.get_hash()) + \
                       "' data-category='" + str(self.ne_type) + \
                       "' data-case='" + str(self.case) + \
                       "' data-lemma='" + str(self.lemma.strip()) + \
                       "' data-link='" + str(self.get_links(filter="wikipedia")) + \
                       "' data-location='" + str(self.get_sentence_start_idx()) + "'>" + str(
                    self.string.strip()) + "</span>"

            logger.info("Return html=%s", html)
            return html

    def render_links_to_html(self, display=1):
        hide_div = ""
        if display == 0:
            hide_div = "style='display:none'"
        links = self.get_links().split(',')
        html_links = ["<a href='" + l.strip() + "' target='_blank'> " + l.replace("http://", "").split("/")[
            0] + " (" + self.string.strip() + ") </a><br>" for l in links if "http://" in l]
        content = "<div class='popover-content-div' " + hide_div + " data-links='" + self.get_links(
            filter="wikipedia") + "'>" + "".join(html_links) + "</div>"
        logger.debug("Return content=%s", content)
        return content

    def render_json(self, context=False):
        # original forms
        original_forms = set([n.get_string() for n in self.get_related()])

        if self.get_string() not in original_forms:
            original_forms.add(self.get_string())

        # renders entity to json
        json_data = {'id': self.get_hash(),
                     'group': self.id,
                     'baseForm': self.lemma,
                     'category': self.ne_type,
                     'surfaceForm': self.get_string(),
                     'isPlural': self.is_plural(),
                     'alternateLabel': self.alt_label,
                     'locationStart': self.document_char_start_ind[0],
                     'locationEnd': self.document_char_end_ind[0],
                     'case': self.get_case().upper(),
                     'positionInSentence': self.sentence_location_start,
                     'method': self.method,
                     'sentence': self.sentence.get_id(),
                     'paragraph': self.sentence.paragraph.get_id()}

        if len(self.relatedMatches.keys()) > 0:
            json_data['link'] = self.get_links().split(',')
            json_data['relatedLinks'] = self.get_related_links()

        if context > 0:
            print("Has context")
            print(self.c_titles)
            print(self.c_gender)
            print(self.c_dates)
            if len(self.c_titles) > 0:
                json_data['titles'] = self.get_titles()
            if len(self.c_gender) > 0:
                json_data['gender'] = self.get_gender()
            if len(self.c_dates) > 0:
                json_data['lifespan'] = self.get_dates()
        print(json_data)
        return self.hash, json_data

    def __repr__(self):
        return "'" + self.string + "'" + " (#" + str(self.id) + ", @type=" + self.ne_type + ", @loc=" + str(
            self.start_ind) + "-" + str(self.end_ind) + ", @score=" + str(self.get_total_score()) + "(" + str(
            self.score) + ")" + ", @methods=" + str(self.method) + ")"

    def __str__(self):
        return "'" + self.string + "'" + " (#" + str(self.id) + ", @type=" + self.ne_type + ",  @loc=" + str(
            self.start_ind) + "-" + str(self.end_ind) + ", " + str(self.start_char_ind) + "-" + str(
            self.end_char_ind) + ", @score=" + str(self.get_total_score()) + "(" + str(
            self.score) + ")" + ")" + ", @methods=" + str(self.method) + ")"

    def __hash__(self):
        return id(self)

    def __eq__(self, other):

        if other == None:
            return False

        if self.ne_type != other.get_type():
            return False

        if self.string.strip() != other.get_string().strip():
            return False

        if self.start_ind != other.get_start_ind() and self.end_ind != other.get_end_ind():
            return False

        return True
