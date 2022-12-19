from abc import ABC, abstractmethod

class RunTool(ABC):

    @abstractmethod
    def run(self, multiprocess=False):
        pass

    @abstractmethod
    def execute_tool(self, data):
        pass

    @abstractmethod
    def check_status(self, json_data):
        pass