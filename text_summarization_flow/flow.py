from os import PathLike
from pathlib import Path

from pocketflow import BatchNode, Flow, Node
from utils.llm_utils import call_llm


class LoadFile(Node[PathLike, str, None]):
    def prep(self, shared):
        return shared["filepath"]

    def exec(self, prep_res: PathLike):
        prep_res = Path(prep_res)
        return open(prep_res, "r").read()

    def post(self, shared, prep_res, exec_res):
        shared["raw"] = exec_res


class Summarize(Node[str, str, None]):
    def prep(self, shared):
        return shared["raw"]

    def exec(self, prep_res: str):
        prompt = f"Summaryize in exactly 10 words: {prep_res}"
        return call_llm(prompt)

    def post(self, shared, prep_res, exec_res):
        shared["summary"] = exec_res


class PrintResult(Node[str, None, None]):
    def prep(self, shared):
        return shared["summary"]

    def exec(self, prep_res: str):
        print("== Summary ==\n", prep_res)


# Wire up the flow
load, summarize, printer = LoadFile(), Summarize(), PrintResult()
load >> summarize >> printer

my_flow = Flow(start=load)
