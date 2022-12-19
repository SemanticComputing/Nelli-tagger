# Tagger

## About

Nelli or Nelli-tagger is a named entity linking tool that extracts NEs using various NER tools and disambiguates them using a voting/scoring scheme. The tool combines the benefits of different NER tools and combination with entity linking, it can recognize and link entities to the user-specified dictionaries or ontologies. Here, the extracted entities at a specific location in text are compared to each other and the most popular result for the given location is selected. The scheme takes also into consideration linkage and length of the entity, considering it more precise if the entity label is longer and it has been linked to a user specified  ontology. The tool can also return entities that are not linked to an ontology. The tool can process text in xml-based formats or as plain text. The results are provided in JSON format.

### API

The service has also a usable API for testing. The service API description can be found from [Swagger](https://app.swaggerhub.com/apis-docs/SeCo/nlp.ldf.fi/1.0.0#/nelli/).

### Publications

* Minna Tamper, Arttu Oksanen, Jouni Tuominen, Aki Hietanen and Eero Hyvönen: Automatic Annotation Service APPI: Named Entity Linking in Legal Domain. The Semantic Web: ESWC 2020 Satellite Events (Harth, Andreas, Presutti, Valentina, Troncy, Raphaël, Acosta, Maribel, Polleres, Axel, Fernández, Javier D., Xavier Parreira, Josiane, Hartig, Olaf, Hose, Katja and Cochez, Michael (eds.)), Lecture Notes in Computer Science, vol. 12124, pp. 208-213, Springer-Verlag, 2020.
* Minna Tamper, Eero Hyvönen and Petri Leskinen: Visualizing and Analyzing Networks of Named Entities in Biographical Dictionaries for Digital Humanities Research. Proceedings of the 20th International Conference on Computational Linguistics and Intelligent Text Processing (CICling 2019), Springer-Verlag, October, 2021. Forth-coming.

## Getting Started

To execute, set environment variables:
* ``` export FLASK_APP=src/run.py ```

Then run ``` flask run ```

### Prerequisites

Uses Python 3.5 or newer
Python libraries: flask, requests, nltk
For more details, check the ```requirements.txt``` file.

The environment and its dependensies can be found from ```requirements.txt``` file.

### Configurations

The configurations for Tagger can be found in the ```confs/services.ini```.

Each tool has a section for its setup. Each tool should define the following parameters.

* url: The service url (i.e., http://nlp.ldf.fi/finer)
* pool_size: (default: 4) Pool size sets how many items of the iterable you pass to Pool.map, are distributed per single worker-process at once in what Pool calls a "task".
* pool_number: (default: 4) number of worker processes used to process the texts. This impacts how many cores are used by the application.
* input_feed_level (default: sentence) The size and unit of the input document that is given to the tool (options: sentence, paragraph, fulltext).
* lemmatize (default: false)

#### Runtime configurations and parameters

In addition, when sending requests to the application the user can give the following parameters:

* tools that are going to be used
    * finbert: [TurkuNLP's BERT for Finnish](https://github.com/TurkuNLP/FinBERT).
    * las_linfer: [Lexical Analysis Tool (LAS)](http://demo.seco.tkk.fi/las/) coupled with Linfer.
    * las: Lexical Analysis Tool (LAS) coupled without Linfer. If depparser or las is not set (with or without Linfer) the application uses LAS without Linfer.
    * depparser_linfer: [TurkuNLP's Finnish Dependency](https://turkunlp.org/Finnish-dep-parser/) or [Neural](https://turkunlp.org/Turku-neural-parser-pipeline/) Parser coupled with Linfer.
    * depparser: TurkuNLP's Finnish Dependency Parser coupled without Linfer.
    * finer: [Finclarin's FiNER](https://www.kielipankki.fi/tools/demo/) for named entity recognition.
    * regex: [Regular expression based named entity recognition tool, Reksi](https://version.aalto.fi/gitlab/seco/regex-service).
    * namefinder: [Person Name Finder](https://version.aalto.fi/gitlab/seco/name-finder) for identifying person names and more context from texts.
        * nf_context: whether the user wants to search for context. Parameter is a numeral value, values between 1-99 equals to querying all context. However, if the user wants to get for example only gender or titles for the PersonName named entity, it is possible to do this using values larger than 100. In this usecase, the application interprets numbers larger than 1 as True and 1 or smaller as False. The numbers are mapped to context as follows: in 123, 1 is for titles (value is false), 2 is for gender (value is true), and 3 is for dates (value is True). In this case the application extracts possibly the gender of the name and the dates followed by the name. Similarly if the value of context is 200, the application extracts only titles related to the name. For more documentation about the features in namefinder, see the [Readme](https://version.aalto.fi/gitlab/seco/name-finder).
    * linking: if the results will be linked and this will be followed by set of [ARPA](https://demo.seco.tkk.fi/arpa-ui) configurations.
        * domain: ARPA configurations listed for domain knowledge.
        * place: ARPA configurations listed for places.
        * time: ARPA configurations listed for time references.
        * organization: ARPA configurations listed for organizations.
        * person: ARPA configurations listed for people.
* categories: which named entities need to be listed on the result set
* modified: if the annotations will be added into the text for displaying as html

The input text will be given as raw data with content-type parameter. The content-type can be text/plain, application/octet-stream, text/xml, or text/html.

By default the application uses FinBERT and las (without Linfer) if the tools are not configured.

#### Logging configuration

The configurations for logging are in the logs/confs/run.ini file. In production, the configurations should be set to WARNING mode in all log files to limit the amount of logging to only errors. The INFO and DEBUG logging modes serve better the debugging in the development environment.

## Usage

Querying results with Content-type: application/octet-stream for given document.
```
curl -d @xml/example.xml -H "Content-type: application/octet-stream" localhost:5000/tagger
```

Querying results with Content-type: text/xml for given xml.
```
curl -d "<p>Ulkomaisen tavaramerkin x haltija A oli purkanut ulkomaalaisen alihankkijansa B:n kanssa tekemänsä hankintasopimuksen ja ilmoittanut, että tuotteet olivat B:n käytettävissä. Tällä ilmoituksella B ei ollut saanut lupaa xtavaramerkillä merkittyjen tuotteiden laskemiseen liikkeeseen. C, joka toi B:ltä ostettuja x-merkillä varustettuja tuotteita maahan, loukkasi sen vuoksi A:n tytäryhtiön D:n yksinoikeutta x-merkkiin.</p>" -H "Content-type: text/xml" localhost:5000/tagger
```

Querying results with Content-type: text/plain for given text.
```
curl -X POST \
  'http://localhost:5000/tagger?finbert=1&finer=0&las=0&depparser=0&regex=0&name-finder=0' \
  -H 'Content-Type: text/plain' \
  -H 'cache-control: no-cache' \
  -d '
Selostus asian aikaisemman käsittelyn vaiheista

 Itä-Uudenmaan työvoima- ja elinkeinokeskus  on päätöksellään 23.11.1988 Mikämikämaan merenneidot ry:n hakemuksesta kieltänyt kalastuslain 8 §:n 1 momentissa tarkoitetun onkimisen, pilkkimisen ja viehekalastuksen Mysteeri kunnan Kuvitteellisessa kylässä sijaitsevassa Poukamalahdessa ajalla 15.12.1987-28.4.1988 seuraavilla ehdoilla:

1) Hakijan on vuosittain joulukuun loppuun mennessä toimitettava työvoima- ja elinkeinokeskukselle selvitys siitä, että vesialuetta hoidetaan ja käytetään hakemuksessa esitetyllä tavalla. Selvityksen tulee sisältää tiedot istutuksista, kalastajamääristä ja saaliista.

2) Kieltopäätös voidaan kumota, mikäli kalastusoikeuden haltija sitä pyytää tai Poukamalahden käyttötarkoitus muuttuu.
```

Querying results with Content-type: text/html for given html.
```
curl -X POST \
  'http://localhost:5000/tagger?finbert=1&finer=0&las=0&depparser=0&regex=0&name-finder=0' \
  -H 'Content-Type: text/html' \
  -H 'cache-control: no-cache' \
  -d '<html>
<body>
<h1>Selostus asian aikaisemman käsittelyn vaiheista</h1>
<p>
 Itä-Uudenmaan työvoima- ja elinkeinokeskus  on päätöksellään 23.11.1988 Mikämikämaan merenneidot ry:n hakemuksesta kieltänyt kalastuslain 8 §:n 1 momentissa tarkoitetun onkimisen, pilkkimisen ja viehekalastuksen Mysteeri kunnan Kuvitteellisessa kylässä sijaitsevassa Poukamalahdessa ajalla 15.12.1987-28.4.1988 seuraavilla ehdoilla:
</p>
<p>
1) Hakijan on vuosittain joulukuun loppuun mennessä toimitettava työvoima- ja elinkeinokeskukselle selvitys siitä, että vesialuetta hoidetaan ja käytetään hakemuksessa esitetyllä tavalla. Selvityksen tulee sisältää tiedot istutuksista, kalastajamääristä ja saaliista.
</p>
<p>
2) Kieltopäätös voidaan kumota, mikäli kalastusoikeuden haltija sitä pyytää tai Poukamalahden käyttötarkoitus muuttuu.
</p>
</body>
</html>'
```

### Output

Example output:

```
{"entities": [
  {
   "alternateLabel": "",
   "baseForm": "Sauli Väinämö Niinistö",
   "case": "Nom",
   "category": "PersonName",
   "group": 1,
   "id": "b281e612fcb9bd0ae022925f64efaa6d",
   "isPlural": false,
   "locationEnd": 22,
   "locationStart": 0,
   "method": [
    "Linguistic Rules",
    "finbert",
    "name-finder"
   ],
   "positionInSentence": 0,
   "surfaceForm": "Sauli Väinämö Niinistö"
  },
  {
   "alternateLabel": "",
   "baseForm": "Suomi",
   "case": "Gen",
   "category": "PersonName",
   "group": 2,
   "id": "63a3fdffb925abbf021aa857a8033ed7",
   "isPlural": false,
   "locationEnd": 32,
   "locationStart": 26,
   "method": [
    "Linguistic Rules",
    "name-finder"
   ],
   "positionInSentence": 4,
   "surfaceForm": "Suomen"
  },
  {
   "alternateLabel": "",
   "baseForm": "1 maaliskuu 2012",
   "case": "",
   "category": "ExpressionTime",
   "group": 3,
   "id": "a77794dabe38fde76a6e7e82ef95b76c",
   "isPlural": true,
   "locationEnd": 99,
   "locationStart": 80,
   "method": [
    "finer",
    "finbert",
    "regex"
   ],
   "positionInSentence": 3,
   "surfaceForm": "1. maaliskuuta 2012"
  },
  {
   "alternateLabel": "",
   "baseForm": "tammikuu 2018",
   "case": "",
   "category": "ExpressionTime",
   "group": 4,
   "id": "eb4c9b4c1d93ef400b5e1efce96f5c35",
   "isPlural": true,
   "locationEnd": 170,
   "locationStart": 154,
   "method": [
    "finer",
    "finbert",
    "regex"
   ],
   "positionInSentence": 12,
   "surfaceForm": "tammikuussa 2018"
  },
  {
   "alternateLabel": "",
   "baseForm": "1.2.2018",
   "case": "",
   "category": "ExpressionTime",
   "group": 5,
   "id": "f55e9524449f777466df9a443de2a946",
   "isPlural": true,
   "locationEnd": 199,
   "locationStart": 191,
   "method": [
    "finer",
    "finbert",
    "regex"
   ],
   "positionInSentence": 3,
   "surfaceForm": "1.2.2018"
  }
 ]
}
```

The API returns a JSON response that contains the status_code where 200 is a success and -1 represents error. In both cases the data is contained in the data field. In case of errors the error message, code, reason are in their own fields. In case of successful execution, the data contains the resultset with list of entities found in text. In the resultset the sentences are index from 0 to n and each sentence has its named entities, index in sentence (nth word), type and the string.
The results contains the original text (that can be modified, if wanted) and a list of entities.

Complete list of possible variables depending on the tools used:
* alternateLabel - alternative forms of the same entity in text, for example references to a person with family name
* baseForm - lemma form of the entity in text
* case - case of the entity
* category - named entity type
* group - an id that groups this entity to other instances of the same entity (related to alternateLabel)
* id - individual id for this named entity
* isPlural - if the entity is in plural or singular form
* locationEnd - character location, the first character of this entity
* locationStart - character location, the last character of this entity
* method - list of methods that have identified this entity
* positionInSentence - index in sentence (nth word)
* surfaceForm - original form of the entity in text

## Dev & Test

For testing the modifications made into the application run: `python -m unittest discover` 

## Running in Docker

`docker-compose up`: builds and runs Tagger and the needed backend services

The configuration parameters for the used tools (IP/host, port) must be passed as environment variables to the container.

For example, the following configuration parameters must be passed, if the default tools (FinBERT-NER and LAS) are used:

FinBERT-NER:

* IP_BACKEND_FINBERT_NER
* PORT_BACKEND_FINBERT_NER

LAS:

* IP_BACKEND_LAS_WRAPPER
* PORT_BACKEND_LAS_WRAPPER
* IP_BACKEND_LAS
* PORT_BACKEND_LAS

If other tools are used (by specifying them in the HTTP request), the following configuration parameters must be passed:

FiNER:

* IP_BACKEND_FINER_WRAPPER
* PORT_BACKEND_FINER_WRAPPER

Turku neural parser:

* IP_BACKEND_FIN_DEP_PARSER_WRAPPER
* PORT_BACKEND_FIN_DEP_PARSER_WRAPPER

Instead of Turku neural parser, Finnish Dependency Parser parser can be used (using these same configuration parameters). In that case, the configuration for DEPPARSER's `input_feed_level` has to be set to `paragraph` in `/app/confs/services.ini`.

Name Finder:

* IP_BACKEND_NAME_FINDER
* PORT_BACKEND_NAME_FINDER

Regex service:

* IP_BACKEND_REGEX
* PORT_BACKEND_REGEX

Other configuration parameters should be set by using a services.ini file (see section Configurations above) which can be e.g. bind mounted to container's path `/app/confs/services.ini`.

The log level can be specified by passing the following environment variable to the container:

* LOG_LEVEL
