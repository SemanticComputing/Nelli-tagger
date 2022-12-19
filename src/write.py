from rdflib import URIRef, Literal, Graph
from rdflib.namespace import RDF, DCTERMS, XSD
import logging

logger = logging.getLogger('Write')
hdlr = logging.FileHandler('write.log')
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)
class Writer:

    def __init__(self, ind, ned):
        self.filename = ""
        self.format = ""
        self.g = Graph()
        self.ind = int(ind) #433961
        self.group_ind = int(ned) #222524

    def get_ind(self):
        return self.ind

    def set_ind(self, idx):
        self.ind = idx

    def set_writer(self, outfile, outformat):
        self.filename = outfile
        self.format = outformat

    def write_ne_types(self):
        nes = {"PersonName": 8, "PlaceName": 5, "OrganizationName": 6, "ExpressionTime": 7,
                            "AddressName": 2, "PoliticalLocation": 4, "GeographicalLocation": 3,
                            "EducationalOrganization": 5, "VocationName":4, "AnonymEntity": 1,
                            "CorporationsName":6, "SportsOrganizations":6,
                            "CultureOrganization":6, "PoliticalOrganization":6,
                            "MediaOrganization":6, "Title":4 }
        nbfp = "http://ldf.fi/nbf/biography/data#"
        nbf = "http://ldf.fi/nbf/biography/"
        nbf_ne = URIRef(nbf + "NamedEntityType")
        type_score = URIRef(nbfp + '#score')
        for ne in nes:
            nbf_ne_type = URIRef(nbf + ne)
            score = Literal(int(nes[ne]), datatype=XSD.integer)

            self.g.add((nbf_ne_type, RDF.type, nbf_ne))
            self.g.add((nbf_ne_type, type_score, score))

    def write(self, sentences, uri):
        nbfp = "http://ldf.fi/nbf/biography/data#"
        nbf = "http://ldf.fi/nbf/biography/"
        skos_related_match = URIRef("http://www.w3.org/2004/02/skos/core#relatedMatch")
        if not (uri.endswith('/')):
            uri = uri + "/"
        nbf = uri

        nbf_ne = URIRef(nbf + "NamedEntity")
        nbf_ned = URIRef(nbf + "NeMethod")
        begin_point = URIRef(nbf + 'data#startPoint')
        end_point = URIRef(nbf + 'data#endPoint')
        begin_index = URIRef(u'http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#beginIndex')
        end_index = URIRef(u'http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#endIndex')
        is_string = URIRef(u'http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#isString')
        nbf_ne_type_prop = URIRef(nbf+'data#namedEntityType')
        nbf_has_ne = URIRef(nbf+'data#hasNamedEntity')
        nbf_has_ne_group = URIRef(nbf + 'data#hasNamedEntityGroup')
        nbf_used_ned = URIRef(nbf+'data#usedNeMethod')
        nbf_method = URIRef(nbf+'data#method')
        nbf_score = URIRef(nbf+'data#score')
        nbf_primary = URIRef(nbf+'data#primary')
        nbf_group_member = URIRef(nbf + 'data#member')
        nbf_ne_lemma = URIRef(nbf + 'data#lemma')

        for sid in sentences:
            sentence = sentences[sid]
            nes = sentence.get_nes()
            if len(nes) > 0:

                longest_nes = sentence.find_longest_ne()
                sentence_uri = URIRef(sentence.get_uri())
                ne_groups, group_primaries = self.get_ne_groups(nbf, sentence, nbf_has_ne_group, sentence_uri)

                for ne in nes:
                    nbf_ne_uri = URIRef(nbf + "NamedEntity/ne" + str(self.ind))
                    nbf_ned_uri = URIRef(nbf + "NeMethod/ned" + str(self.ind))
                    nbf_ne_type = URIRef(nbf + ne.get_type())
                    method = Literal(ne.get_method())
                    score = Literal(ne.get_score(), datatype=XSD.integer)
                    longest = Literal(1, datatype=XSD.integer)
                    other = Literal(0, datatype=XSD.integer)
                    ne_in_group = False
                    ne_in_group = self.write_ne_group(group_primaries, nbf_group_member, nbf_ne_uri, nbf_primary, ne,
                                                      ne_groups, ne_in_group)

                    if ne_in_group == False:
                        nbf_negroup_uri = URIRef(nbf + "NamedEntityGroup/neg" + str(self.group_ind))
                        self.group_ind = self.group_ind + 1
                        self.g.add((nbf_negroup_uri, nbf_group_member, nbf_ne_uri))
                        self.g.add((nbf_negroup_uri, nbf_primary, nbf_ne_uri))


                    begin_index_value = Literal(ne.get_start_ind())
                    end_index_value = Literal(ne.get_end_ind())
                    is_string_value = Literal(ne.get_string())

                    self.g.add((nbf_ne_uri, RDF.type, nbf_ne))
                    self.g.add((nbf_ne_uri, begin_index, begin_index_value))
                    self.g.add((nbf_ne_uri, end_index, end_index_value))
                    self.g.add((nbf_ne_uri, is_string, is_string_value))
                    self.g.add((nbf_ne_uri, nbf_ne_type_prop, nbf_ne_type))
                    self.g.add((nbf_ne_uri, nbf_used_ned, nbf_ned_uri))

                    for lemma, link in ne.get_related_matches().items():
                        match = URIRef(link)
                        label = Literal(lemma, datatype=XSD.string)
                        self.g.add((nbf_ne_uri, skos_related_match, match)) #nbf_ne_lemma
                        self.g.add((nbf_ne_uri, nbf_ne_lemma, label))  # nbf_ne_lemma


                    self.g.add((nbf_ned_uri, RDF.type, nbf_ned))
                    self.g.add((nbf_ned_uri, nbf_method, method))
                    self.g.add((nbf_ned_uri, nbf_score, score))
                    self.g.add((sentence_uri, nbf_has_ne, nbf_ne_uri))
                    self.get_words_for_ne(sentence, ne, self.g, nbf_ne_uri)

                    self.ind=self.ind+1

    def write_ne_group(self, max_nes, nbf_group_member, nbf_ne_uri, nbf_primary, ne, ne_groups, ne_in_group):
        max_ne = None
        for nbf_negroup_uri in ne_groups:
            group = ne_groups[nbf_negroup_uri]
            if ne in group:
                logging.info("Adding to group %s ne %s", nbf_negroup_uri, ne.get_string())
                ne_in_group = True
                self.g.add((nbf_negroup_uri, nbf_group_member, nbf_ne_uri))
                if ne == max_nes[nbf_negroup_uri]:
                    self.g.add((nbf_negroup_uri, nbf_primary, nbf_ne_uri))
        return ne_in_group

    def get_ne_groups(self, nbf, sentence, nbf_has_ne, sentence_uri):
        is_part_of = URIRef(u'http://purl.org/dc/terms/isPartOf')
        ne_group = sentence.ne_intersection()
        ne_groups = dict()
        ne_group_primarys = dict()
        for i in ne_group:
            nbf_negroup_uri = URIRef(nbf + "NamedEntityGroup/neg" + str(self.group_ind))
            self.g.add((sentence_uri, nbf_has_ne, nbf_negroup_uri))
            self.g.add((nbf_negroup_uri, is_part_of, sentence_uri))
            self.group_ind = self.group_ind + 1
            ne_groups[nbf_negroup_uri] = ne_group[i]
            max_score = 0
            for member in ne_group[i]:
                if member.get_total_score() >= max_score:
                    ne_group_primarys[nbf_negroup_uri] = member
                    max_score = member.get_total_score()

        return ne_groups, ne_group_primarys

    def serialize_file(self):
        self.g.serialize(destination=self.filename, format=self.format)
        self.g = Graph()

    def get_words_for_ne(self, sentence, ne, g, ne_uri):
        start_inds = ne.get_start_ind()
        end_inds = ne.get_end_ind()
        words = sentence.get_words()
        is_part_of = URIRef(u'http://purl.org/dc/terms/isPartOf')
        for i in enumerate(start_inds):
            start_ind = start_inds[i]
            end_ind = end_inds[i]+1
            for j in range(start_ind, end_ind):
                if j in words:
                    wid = words[j].get_uri()
                    word_uri = URIRef(wid)
                    g.add((word_uri, is_part_of, ne_uri))