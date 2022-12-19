
import math
import logging, logging.config
import time
import datetime
import collections
import requests
from src.ner.run_tool import RunTool
from concurrent.futures import ThreadPoolExecutor


logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('finbert')


class RunFinBert(RunTool):
    def __init__(self, directory, file_pattern, tool, input_texts, pool_number, pool_size):
        self.input_texts = list()
        if len(input_texts)>0:
            self.input_texts = input_texts

        self.folder = directory
        if not (self.folder.endswith("/")):
            self.folder += "/"

        self.file_extension = file_pattern
        self.output_files = dict()

        if len(tool) > 2:
            self.tool = tool
        else:
            self.tool = ""

        self.pool_number = pool_number
        self.pool_size = pool_size

    def run(self, multiprocess=False):
        items = list(self.input_texts.items())

        if multiprocess and len(items)>1:
            start = time.time()
            pool = ThreadPoolExecutor(self.pool_number)

            chunk_dict = collections.OrderedDict()
            chunk_dict_tmp = collections.OrderedDict()
            chunk_dict = {i:"" for i in range(0, len(items))}
            chunk_dict_tmp = {i: "" for i in range(0, len(items))}
            for item, string in self.input_texts.items():
                st, p, s = item.split("_")
                if p not in chunk_dict_tmp:
                    chunk_dict_tmp[p] = dict()
                chunk_dict_tmp[p][int(s)] = string

            # sort sentences in paragraph
            for key, val in chunk_dict_tmp.items():
                if len(val) > 0:
                    sorted_dict = sorted(val.items())
                    chunk_dict[int(key)] = ' '.join(str(x[1]) for x in sorted_dict)

            tmp = {k: v for k, v in chunk_dict.items() if len(v) > 1}
            items = list(tmp.items())
            logger.debug('Multiprocessing items: %s (%s)', items, chunk_dict)
            chunksize = math.ceil(len(items)/self.pool_size)
            chunks = [items[i:i + chunksize] for i in range(0, len(items), chunksize)]

            logger.debug('Multiprocessing chunks: %s',chunks)

            files = pool.map(self.execute_tool, chunks)

            for i, output in enumerate(files):
                self.output_files[i] = output
            end = time.time()
            logger.info("[STATUS] Executed FinBert queries using multiprocessing in %s", str(datetime.timedelta(seconds=(end - start))))
        else:
            start = time.time()
            results = self.execute_tool(items)
            self.output_files = results
            end = time.time()
            logger.info("[STATUS] Executed FinBert queries using single input in %s",
                        str(datetime.timedelta(seconds=(end - start))))

    def execute_tool(self, data):

        logger.info("[STATUS] Start a worker for data %s ", data)

        url = 'http://nlp.ldf.fi/finbert-ner'
        url = 'http://86.50.253.19:8001/tagdemo/tag'
        url = self.tool
        results = dict()
        t = ""
        try:
            for tpl in data:
                if len(tpl[1]) > 1:
                    ind =tpl[0]

                    params = dict(
                        text=tpl[1],
                        format='json'
                    )

                    start = time.time()
                    logger.debug("[FINBERT] execute-tool %s: %s",url, params)
                    resp = requests.get(url=url, params=params)
                    end = time.time()
                    logger.info('Response %s, took %s (started %s), for query %s', resp, str(datetime.timedelta(seconds=(end - start))), str(start), tpl[1])
                    if resp.status_code == 200:
                        data = resp.json()  # Check the JSON Response Content documentation below
                        logger.info("Response %s", data)
                        if data != None:
                            logger.debug("FinBert result: %s for ind=%s", data, ind)
                            if len(data)>0:
                                results[ind] = data
                            else:
                                logger.info('Results %s', data)
                    else:
                        logger.warning('Error %s for text %s', resp.status_code, tpl[1])
        except Exception as err:
            logger.warning("Error occured why trying to run tool:", self.tool)
            logger.error(err)
        return results

    def check_status(self, json_data):
        logger.debug('Checking results %s', str(json_data))
        if json_data['status'] == 200:
            return json_data['data']
        else:
            return None

    def get_output_files(self):
        return self.output_files

    def get_input_files(self):
        return self.input_texts

    def get_tool(self):
        return self.tool

    def set_tool(self, tool):
        self.tool = tool

    def set_input_files(self, input):
        self.input_texts = input

