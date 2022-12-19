#!nerdl/bin/python3
from flask import Flask, Response
from flask import request
import sys, os
from src.structure.document import Document
from src.ner.las.parse_las_results import NerLas
from src.ner.depparser.parse_depparser_results import NerDepParser
from src.ner.finer.parse_finer_results import NerFiner
from src.ner.finbert.parse_finbert_results import NerFinBert
from src.ner.regex.parse_regex_results import NerRegex
from src.ner.nescore import NeScore
from src.ner.namefinder.parse_namefinder_results import NerNameFinder
from src.nel.named_entity_linking import NamedEntityLinking
import time
import datetime
import logging.config
from flask_cors import CORS, cross_origin
import urllib
from flask_restful import reqparse
import cgi
import traceback
from flask import jsonify
from datetime import datetime as dt
from src import app
from flask import json, redirect
# import src.feedback as fb
from src.ThreadingTaggerApp import ThreadWithReturnValue
from collections import OrderedDict

# arpas
arpa_configurations = dict()
endpoint = ""
graph = ""
uri = ""
file_id = 0

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('core')


@app.before_request
def before_request():
    if True:
        logger.info("HEADERS, %s", request.headers)
        logger.info("REQ_path, %s", request.path)
        logger.info("ARGS, %s", request.args)
        logger.info("DATA, %s", request.data)
        logger.info("FORM, %s", request.form)


def parse_params():
    logger.info("REG.ARGS, %s", request.args)
    parser = reqparse.RequestParser()
    parser.add_argument('place')
    parser.add_argument('time')
    parser.add_argument('person')
    parser.add_argument('organization')
    parser.add_argument('domain')
    parser.add_argument('statute')
    parser.add_argument('caselaw')
    parser.add_argument('linking')  # put spans inside links
    parser.add_argument('finer')
    parser.add_argument('finbert')
    parser.add_argument('las')
    parser.add_argument('las_linfer')
    parser.add_argument('depparser_linfer')
    parser.add_argument('regex')
    parser.add_argument('depparser')
    parser.add_argument('namefinder')
    parser.add_argument('categories')
    parser.add_argument('modified')
    parser.add_argument('content')
    parser.add_argument('get_morphological_analysis')
    parser.add_argument('supportedLanguages')
    parser.add_argument('nf_context')

    args = parser.parse_args()

    logger.info("ARGS, %s", args)
    logger.debug("ARGS ", args)

    # init arpa and setup lists for configs
    arpas = dict()
    settup = dict()

    # default setup, used when nothing is defined
    # main services
    settup['finer'] = 0
    settup['regex'] = 0
    settup['las'] = 0
    settup['finbert'] = 1

    # additional services
    settup['las_linfer'] = 0
    settup['depparser_linfer'] = 0
    settup['depparser'] = 0
    settup['namefinder'] = 0
    settup['linking'] = 0
    settup['modified'] = 0
    settup['content'] = 1
    settup['entities'] = 1
    settup['get_morphological_analysis'] = 0
    settup['categories'] = ''
    settup['supportedLanguages'] = ''
    settup['nf_context'] = 0

    if 'time' in args:
        if args['time'] != None:
            arpas['ExpressionTime'] = args['time'].split(",")
    if 'place' in args:
        if args['place'] != None:
            arpas['PlaceName'] = args['place'].split(",")
    if 'person' in args:
        if args['person'] != None:
            arpas['PersonName'] = args['person'].split(",")
    if 'organization' in args:
        if args['organization'] != None:
            arpas['OrganizationName'] = args['organization'].split(",")
    if 'vocation' in args:
        if args['vocation'] != None:
            arpas['VocationName'] = args['vocation'].split(",")
    if 'domain' in args:
        if args['domain'] != None:
            arpas['DomainKnowledge'] = args['domain'].split(",")
    if 'statute' in args:
        if args['statute'] != None:
            arpas['Statutes'] = args['statute'].split(",")
    if 'caselaw' in args:
        if args['caselaw'] != None:
            arpas['CourtDecision'] = args['caselaw'].split(",")
    if 'categories' in args:
        if args['categories'] != None:
            settup['categories'] = str(args['categories']).strip().split(",")

    # lang support
    if 'supportedLanguages' in args:
        if args['supportedLanguages'] != None:
            settup['supportedLanguages'] = str(args['supportedLanguages']).strip().split(",")

    # turning on/off different identifiers and apps
    for setup in settup.keys():
        if setup in settup.keys() and isinstance(settup[setup], int):
            if setup in args:
                settup[setup] = extract_param_from_args(args, setup)
            elif setup in request.form:
                settup[setup] = extract_param_from_args(request.form, setup)

    logger.warning("Ultimate setup: %s", str(settup))

    return arpas, settup


def extract_param_from_args(args, param):
    settup = 0

    if param in args:
        if args[param] != None:
            try:
                logger.info(str(param))
                logger.info(str(int(args[param])))
                settup = int(args[param])
            except Exception as err:
                settup = 0
                logger.warn("Unable to read incoming configs for " + param + ":", str(args))

    return settup


def root_dir():  # pragma: no cover
    return os.path.abspath(os.path.dirname(__file__))


def get_file(filename):  # pragma: no cover
    try:
        src = os.path.join(root_dir(), filename)
        # Figure out how flask returns static files
        # Tried:
        # - render_template
        # - send_file
        # This should not be so non-obvious
        return open(src).read()
    except IOError as exc:
        return str(exc)


@app.route('/docs')
def documentation():
    return redirect("https://app.swaggerhub.com/apis-docs/SeCo/nlp.ldf.fi/1.0.0#/", code=200)


@app.route('/feedback', methods=['POST', 'GET', 'OPTIONS'])
def collect_feedback():
    logger.debug("HEADERS", request.headers)

    return Response("OK", mimetype="text/html")


@app.route('/categories', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin()
def get_categories():
    nes = NeScore()
    categories = list(nes.get_types())
    return jsonify(categories)


@app.route('/tagger', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin()
def api_message():
    content_dict = None
    doc = Document()
    declaration = None
    mimetype, options = cgi.parse_header(request.headers['Content-Type'])

    print("HEADERS", request.headers)
    logger.debug("Type:", request.headers['Content-Type'])
    if mimetype == 'text/plain':
        try:
            logger.debug("Request Data", request.data)
            doc.parse_text(urllib.parse.unquote(str(request.data, 'utf-8')))
        except Exception as err:
            logger.warning("BADLY formed HTML")
            logger.error(err)
            logger.error(traceback.format_exc())
            data = {"status": -1, "error": "Error with input data:" + urllib.parse.unquote(str(request.data, 'utf-8')),
                    "service": "Tagger",
                    "date": dt.today().strftime('%Y-%m-%d')}
            return jsonify(data)

        return jsonify(execute_tagger(doc, text=True))
    elif mimetype == 'text/html':
        try:
            logger.debug("Request Data", request.data)
            declaration = doc.parse_html(urllib.parse.unquote(str(request.data, 'utf-8')))

        except Exception as err:
            logger.warning("BADLY formed HTML")
            logger.error(err)
            logger.error(traceback.format_exc())
            data = {"status": -1, "error": "Error with input data:" + urllib.parse.unquote(str(request.data, 'utf-8')),
                    "service": "Tagger",
                    "date": dt.today().strftime('%Y-%m-%d')}
            return jsonify(data)

        return jsonify(execute_tagger(doc, xml=False, declaration=declaration))

    elif mimetype == 'text/xml':
        try:
            # xml
            logger.debug("Request Data", request.data)
            declaration = doc.parse_xml(urllib.parse.unquote(str(request.data, 'utf-8')))
        except Exception as err:
            logger.warning("BADLY formed HTML")
            logger.error(err)
            logger.error(traceback.format_exc())
            data = {"status": -1, "error": "Error with input data:" + urllib.parse.unquote(str(request.data, 'utf-8')),
                    "service": "Tagger",
                    "date": dt.today().strftime('%Y-%m-%d')}
            return jsonify(data)

        return jsonify(execute_tagger(doc, xml=True, declaration=declaration))

    elif mimetype == "application/octet-stream":
        # xml files
        try:
            # xml
            logger.debug("Request Data", request.data)
            declaration = doc.parse_xml(urllib.parse.unquote(str(request.data, 'utf-8')))
        except Exception as err:
            logger.warning("BADLY formed HTML")
            logger.error(err)
            logger.error(traceback.format_exc())
            data = {"status": -1, "error": "Error with input data:" + urllib.parse.unquote(str(request.data, 'utf-8')),
                    "service": "Tagger",
                    "date": dt.today().strftime('%Y-%m-%d')}
            return jsonify(data)

        return jsonify(execute_tagger(doc, xml=True, declaration=declaration))
    else:
        logger.error("Bad type", mimetype)
        data = {"status": -1, "error": "415 Unsupported Media Type:" + mimetype, "service": "Tagger",
                "date": dt.today().strftime('%Y-%m-%d')}
        return jsonify(data)


def loop_children(xml_string):
    import xml.etree.ElementTree as ET
    tree = ET.ElementTree(ET.fromstring(xml_string))
    for elt in tree.iter():
        xpath = str('//%s[contains(text(),"%s")]' % (elt.tag, elt.text))

def parse_arg_from_requests(arg, **kwargs):
    parse = reqparse.RequestParser()
    parse.add_argument(arg, **kwargs)
    args = parse.parse_args()
    return args[arg]


def process_input(content_dict, doc):
    logger.debug("%s", content_dict)
    for key, val in content_dict.items():
        logger.debug("key, %s", key)
        if key == 'finlex:document':
            logger.debug('dcterms:abstract')
            for k1, v1 in val['dcterms:abstract'].items():
                logger.debug("level 1, %s", k1)
            logger.debug('finlex:content, %s', val.keys())
            logger.debug('finlex:content > %s', val['finlex:content'].keys())
            logger.debug('finlex:content > %s', val['finlex:content']['div'])
            doc.parse(val['finlex:content']['div'])

    return execute_tagger(doc, xml=True)


def execute_tagger(doc, xml=False, docxml=False, text=False, declaration=None):
    arpa_configurations, setup = parse_params()
    logger.info("Configurations: %s", str(arpa_configurations))
    logger.info("Setups: %s", str(setup))
    threads = OrderedDict()
    results = OrderedDict()

    # Dep-parser
    if setup['depparser'] > 0:
        logger.info("[STATUS] Run Dep-Parser")
        start = time.time()
        dparser = NerDepParser(doc, None)
        results[dparser] = None
        threads[dparser] = ThreadWithReturnValue(target=dparser.run_tool, args=(False,))
        end = time.time()
        logger.info("[STATUS] Executed Dep-Parser in %s", str(datetime.timedelta(seconds=(end - start))))

    # Dep-parser with linfer
    elif setup['depparser_linfer'] > 0:
        logger.info("[STATUS] Run Dep-Parser with Linfer")
        start = time.time(0)
        dparser = NerDepParser(doc, None)
        results[dparser] = None
        threads[dparser] = ThreadWithReturnValue(target=dparser.run_tool, args=(True,))
        end = time.time()
        logger.info("[STATUS] Executed Dep-Parser with Linfer in %s", str(datetime.timedelta(seconds=(end - start))))

    # LAS
    if setup['las'] > 0:
        logger.info("[STATUS] Run LAS")
        start = time.time()
        las = NerLas(doc, None)
        results[las] = None
        threads[las] = ThreadWithReturnValue(target=las.run_tool, args=(False,))
        end = time.time()
        logger.info("[STATUS] Executed LAS in %s", str(datetime.timedelta(seconds=(end - start))))

    # Run LAS with Linfer
    elif setup['las_linfer'] > 0:
        logger.info("[STATUS] Run Linfer with LAS")
        start = time.time()
        las = NerLas(doc, None)
        results[las] = None
        threads[las] = ThreadWithReturnValue(target=las.run_tool, args=(True,))
        end = time.time()
        logger.info("[STATUS] Executed Linfer with LAS in %s", str(datetime.timedelta(seconds=(end - start))))

    # If other tools are disabled, run las without linfer
    if setup['las_linfer'] == 0 and setup['depparser_linfer'] == 0 and setup['depparser'] == 0 and setup['las'] == 0:
        logger.info("[STATUS] Run LAS")
        start = time.time()
        las = NerLas(doc, None)
        results[las] = None
        threads[las] = ThreadWithReturnValue(target=las.run_tool, args=(False,))
        end = time.time()
        logger.info("[STATUS] Executed LAS in %s", str(datetime.timedelta(seconds=(end - start))))

    # Finer
    if setup['finer'] > 0:
        logger.info("[STATUS] Run FINER")
        start = time.time()
        finer = NerFiner(doc, None)
        results[finer] = None
        threads[finer] = ThreadWithReturnValue(target=finer.run_tool)
        end = time.time()
        logger.info("[STATUS] Executed FINER in %s", str(datetime.timedelta(seconds=(end - start))))

    # Finbert
    if setup['finbert'] > 0:
        logger.info("[STATUS] Run FinBERT")
        start = time.time()
        finbert = NerFinBert(doc, None)
        threads[finbert] = ThreadWithReturnValue(target=finbert.run_tool)
        results[finbert] = None
        end = time.time()
        logger.info("[STATUS] Executed FinBERT in %s", str(datetime.timedelta(seconds=(end - start))))

    # Regex
    if setup['regex'] > 0:
        logger.info("[STATUS] Run Regex Identifier")
        start = time.time()
        regex = NerRegex(doc, None)
        threads[regex] = ThreadWithReturnValue(target=regex.run_tool)
        results[regex] = None
        end = time.time()
        logger.info("[STATUS] Executed Regex Identifier in %s", str(datetime.timedelta(seconds=(end - start))))

    # Name-finder: to be added
    if setup['namefinder'] > 0:
        logger.info("[STATUS] Run Name Finder")
        start = time.time()
        namefinder = NerNameFinder(doc, None, context=setup['nf_context'])
        threads[namefinder] = ThreadWithReturnValue(target=namefinder.run_tool)
        results[namefinder] = None
        end = time.time()
        logger.info("[STATUS] Executed Name Finder in %s", str(datetime.timedelta(seconds=(end - start))))

    for tool, thread in threads.items():
        logger.info("Starting %s", tool)
        thread.start()

    for tool, thread in threads.items():
        logger.info("Finishing %s if alive %s", tool, thread.is_alive())
        results[tool] = thread.join()
        logger.info("Result for %s is: %s", tool, results[tool])

    for tool, result in results.items():
        if result != None:
            logger.debug("Got results for %s", tool)
            tool.parse_results(result)

    # Link
    if setup['linking'] > 0:
        logger.info("[STATUS] Run Arpa for %s", str(arpa_configurations.values()))
        start = time.time()

        linker = NamedEntityLinking(doc, None)
        for name, urls in arpa_configurations.items():
            c = 0
            for url in urls:
                c += 1
                logger.info("[STATUS] Set config: %s, %s", name, url)

                linker.create_configuration(name + "_" + str(c), url, False)
        linker.exec_linker()

        end = time.time()
        logger.info("[STATUS] Executed Arpa in %s", str(datetime.timedelta(seconds=(end - start))))

    if xml:
        return doc.render_doc_html(declaration=declaration, return_uniques=False, setup=setup)
    elif docxml:
        return doc.render_doc_xml(return_uniques=False, setup=setup)
    elif text:
        return doc.render_doc_text(return_uniques=False, setup=setup)
    else:
        return doc.render_xml(return_uniques=False, setup=setup)


def parse_structures(structures):
    structs = list()
    for result in structures["results"]["bindings"]:
        struct = result["structure"]["value"]
        structs.append(struct)

    return structs


def write_nes(doc, uri, id, s, writer):
    writer.set_writer(str(id) + "_named_entities_" + str(s) + ".ttl", "turtle")
    for sid, struct in doc.get_structures().items():
        writer.write(struct.get_sentences(), uri)
    writer.serialize_file()


def parse_query_result(results):
    res = ""
    for result in results["results"]["bindings"]:
        w = result["word"]["value"]
        if len(res) <= 0:
            res = w
        else:
            res += " " + w
    return res


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


@app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_server()
    return 'Server shutting down...'


if __name__ == '__main__':
    p = 5002
    h = '0.0.0.0'
    app.run(host=h, port=int(p), debug=True, threaded=True)
