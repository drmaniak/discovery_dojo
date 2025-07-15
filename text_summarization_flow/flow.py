from os import PathLike
from pathlib import Path

from pocketflow import Flow, Node
from utils.llm_utils import call_llm


class LoadFile(Node):
    def prep(self, shared):
        return shared["filepath"]

    def exec(self, filepath: PathLike):
        filepath = Path(filepath)
        return open(filepath, "r").read()

    def post(self, shared, _, text):
        shared["raw"] = text


class Summarize(Node):
    def prep(self, shared):
        return shared["raw"]

    def exec(self, text: str):
        prompt = f"Summaryize in exactly 10 words: {text}"
        return call_llm(prompt)

    def post(self, shared, _, summary):
        shared["summary"] = summary


class PrintResult(Node):
    def prep(self, shared):
        return shared["summary"]

    def exec(self, summary: str):
        print("== Summary ==\n", summary)


# Wire up the flow
load, summarize, printer = LoadFile(), Summarize(), PrintResult()
load >> summarize >> printer

my_flow = Flow(start=load)
