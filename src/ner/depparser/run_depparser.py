
import time
import datetime
import logging, math
import collections
from concurrent.futures import ThreadPoolExecutor
import requests
from src.ner.run_tool import RunTool

logging.config.fileConfig(fname='logs/confs/run.ini', disable_existing_loggers=False)
logger = logging.getLogger('depparser')


class RunDepParser(RunTool):
    def __init__(self, directory, file_pattern, tool, input_texts, pool_number, pool_size, level):
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
        self.level = level

        self.resultset = dict()

    def run(self, multiprocess=False):

        items = list(self.input_texts.items())
        logger.info("Items: %s",items)
        logger.info("Texts: %s",self.input_texts)

        if multiprocess and len(items)>1:
            pool = ThreadPoolExecutor(self.pool_number)

            chunk_dict = collections.OrderedDict()
            chunk_dict_tmp = collections.OrderedDict()

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

            chunksize = math.ceil(len(items) / self.pool_size)
            chunks = [items[i:i + chunksize] for i in range(0, len(items), chunksize)]

            logger.debug('Multiprocessing chunks: %s',chunks)

            files = pool.map(self.execute_tool, chunks)

            for output in files:
                for key, value in output.items():
                    logger.info('[RUN] Process result A (sentence): %s', key)
                    d = value
                    for i, j in d.items():
                        logger.info("[RUN] B key: %s",i)
                        for k, l in j.items():
                            if self.level == 2:
                                identifier = str(key) + "_" + str(key) + "_" + str((int(k) + 1))
                                self.output_files[identifier] = l
                                logger.info('[RUN] Process result C: %s, %s', identifier, l)
                            elif self.level == 3:
                                identifier = str(key) + "_" + str(int(i)+1) + "_" + str((int(k)+1))
                                self.output_files[identifier] = l
                                logger.info('[RUN] Process result C: %s, %s', identifier, l)
        else:
            results = self.execute_tool(items)
            logger.info("RES: %s",results)
            for key, value in results.items():
                logger.info('[RUN] Process result A: %s', key)
                d = value
                self.resultset = value
                for entity in value:
                    i = entity['paragraph']
                    k = entity['sentence']
                    l = entity['words']
                    logger.info("[RUN] B key: %s", i)
                    # TODO: fix indexes to the parse_results.py so that structure id is not same as paragraph id
                    identifier = str(int(i)+1) + "_" + str(int(i)+1) + "_" + str((int(k)+1))
                    self.output_files[identifier] = entity
                    logger.info('[RUN] Process result C: %s, %s', identifier, l)

    def execute_tool(self, data):
        logger.info("%s",data)
        url = self.tool
        results = dict()
        try:
            for tpl in data:
                ind =tpl[0]

                headers = {
                    "Content-Type": "text/plain"
                }
                text = tpl[1]
                if '\n\n' not in tpl[1]:
                    text = tpl[1].replace('\n', '\n\n')

                start = time.time()
                resp = requests.post(url=url, data=text.encode('utf8'), headers=headers)
                end = time.time()
                logger.info('Response (from %s) %s took %s (started %s) for text %s', url, resp,str(datetime.timedelta(seconds=(end - start))),str(start), tpl[1])
                if resp.status_code == 200:
                    data = resp.json()  # Check the JSON Response Content documentation below
                    result = self.check_status(data)
                    if result != None:
                        if len(result) > 0:
                            results[ind] = result
                        else:
                            logger.info('Query text %s', tpl[1])
                            logger.info('Result data %s', data)
                    else:
                        logger.info('Query text %s', tpl[1])
                        logger.info('Results %s', data)
                else:
                    logger.error('Error %s for text %s', resp.status_code, tpl[1])
        except Exception as err:
            logger.warning("Error occured why trying to run tool:", self.tool)
            logger.error(err)
        return results

    def check_status(self, json_data):
        logger.info('Checking results %s', str(json_data))
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

    def get_resultset(self):
        return self.resultset

