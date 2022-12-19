LABEL_PROP = 'label'
"""The name of the property containing the label of the match in the ARPA results."""

TYPE_PROP = 'type'
"""
The name of the property containing the type of the match in the ARPA results->properties.
Only needed for prioritized duplicate removal.
"""

from src.nel.arpa.ArpaQueryExecuter import ArpaQueryExecuter
import json
import logging

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('arpa')

class Arpa:
    """Class representing the ARPA service"""

    def __init__(self, url="", ordered=False, min_ngram_length=1, remove_duplicates=False):
        
        self._url=url
        self._order = ordered

        #self._ignore = [s.lower() for s in ignore or []]
        self._min_ngram_length = min_ngram_length

        if type(remove_duplicates) == bool:
            self._no_duplicates = remove_duplicates
        else:
            self._no_duplicates = tuple("<{}>".format(x) for x in remove_duplicates)
            
    def _get_url(self):
        return self._url

    def _remove_duplicates(self, entries):
        """
        Remove duplicates from the entries.

        A 'duplicate' is an entry with the same `LABEL_PROP` property value.
        If `self._no_duplicates == True`, choose the subject to keep any which way.
        If `self._no_duplicates` is a tuple (or a list), choose the kept subject
        by comparing its type to the types contained in the tuple. The lower the
        index of the type in the tuple, the higher the priority.

        `entries` is the ARPA service results as a JSON object.
        """

        res = entries
        if self._no_duplicates == True:
            labels = set()
            add = labels.add
            res = [x for x in res if not (x[LABEL_PROP] in labels 
                # If the label is not in the labels set, add it to the set.
                # This works because set.add() returns None.
                or add(x[LABEL_PROP]))]

        elif self._no_duplicates:
            # self._no_duplicates is a tuple - prioritize types defined in it
            items = {}
            for x in res:
                x_label = x[LABEL_PROP].lower()
                # Get the types of the latest most preferrable entry that 
                # had the same label as this one
                prev_match_types = items.get(x_label, {}).get('properties', {}).get(TYPE_PROP, [])
                # Get matches from the preferred types for the previously selected entry
                prev_pref = set(prev_match_types).intersection(set(self._no_duplicates))
                try:
                    # Find the priority of the previously selected entry
                    prev_idx = min([self._no_duplicates.index(t) for t in prev_pref])
                except ValueError:
                    # No previous entry or previous entry doesn't have a preferred type
                    prev_idx = float('inf')
                # Get matches in the preferred types for this entry
                pref = set(x['properties'][TYPE_PROP]).intersection(self._no_duplicates)
                try:
                    idx = min([self._no_duplicates.index(t) for t in pref])
                except ValueError:
                    # This one is not of a preferred type
                    idx = float('inf')

                if (not prev_match_types) or idx < prev_idx:
                    # There is no previous entry with this label or
                    # the current match has a higher priority preferred type
                    items[x_label] = x

            res = [x for x in res if x in items.values()]

        return res

    def _filter(self, response):
        """
        Filter matches based on `self._ignore` and remove matches that are
        for ngrams with length less than `self.min_ngram_length`.

        Return the response with the ignored matches removed.

        `response` is the parsed ARPA service response.
        """

        res = response['results']

        if self._order:
            res = self._reverse_order(res)

        # Filter ignored results
        #if self._ignore:
        #    res = [x for x in res if x[LABEL_PROP] != None and x[LABEL_PROP].lower() not in self._ignore]

        # Filter by minimum ngram length
        #if self._min_ngram_length > 1:
        #    res = [x for x in res if len(x['properties']['ngram'][0].split()) >= self._min_ngram_length]

        # Remove duplicates if requested
        res = self._remove_duplicates(res)

        response['results'] = res
        return response

    def _reverse_order(self, res):
        r = [x for x in reversed(res)]
        return r

    def _sanitize(self, text):
        # Remove quotation marks and brackets - ARPA can return an error if they're present
        return text.replace('"', '').replace("(", "").replace(")", "").replace("/", "\/")
    
    def _query(self, querystring):

        url = self._get_url()
        if len(url)>4:
            logger.info("Run url %s", url)
            logger.info("Using text %s", querystring)

            query = ArpaQueryExecuter('',url, querystring)
            result = query.getArpa()

            if 'data' in result:
                res = self._filter(json.loads(result['data']))
                return res
            else:
                return result
        return None
