import sys
from os import PathLike
from pathlib import Path

from pocketflow import Flow, Node
from utils.llm_utils import call_llm


class LoadFile(Node):
    def prep(self, shared):
        shared["filepath"] = Path(shared["filepath"])
        return shared["filepath"]

    def exec(self, prep_res: PathLike):
        return open(prep_res, "r").read()

    def post(self, shared, prep_res, exec_res: str):
        shared["raw"] = exec_res


class DecideLength(Node):
    def prep(self, shared):
        return shared["raw"]

    def exec(self, prep_res: str):
        str_len = len(prep_res.replace("\n", "").replace(" ", ""))
        length: str = ""
        if str_len > 1000:
            print(f"Long text detected with {str_len} characters")
            length = "long"
        else:
            print(f"Short text detected with {str_len} characters")
            length = "short"

        return length

    def post(self, shared, prep_res, exec_res: int):
        shared["length"] = exec_res
        return shared["length"]


class SummarizeShort(Node):
    def prep(self, shared):
        return shared["raw"]

    def exec(self, prep_res: str):
        prompt = f"Summarize in exactly 10 words: {prep_res}"
        return call_llm(prompt)

    def post(self, shared, prep_res, exec_res):
        shared["summary"] = exec_res


class SummarizeLong(Node):
    def prep(self, shared):
        return shared["raw"]

    def exec(self, prep_res: str):
        prompt = f"Summarize in exactly 50 words: {prep_res}"
        return call_llm(prompt)

    def post(self, shared, prep_res, exec_res):
        shared["summary"] = exec_res


class PrintResult(Node):
    def prep(self, shared):
        return shared["summary"]

    def exec(self, prep_res: str):
        print("== Summary ==\n", prep_res)


# Deifne the nodes and flow
load, lencheck, summarize_short, summarize_long, printer = (
    LoadFile(),
    DecideLength(),
    SummarizeShort(),
    SummarizeLong(),
    PrintResult(),
)

load >> lencheck
lencheck - "long" >> summarize_long
lencheck - "short" >> summarize_short
summarize_short >> printer
summarize_long >> printer

my_flow = Flow(start=load)


if __name__ == "__main__":
    shared = {"filepath": sys.argv[1]}
    my_flow.run(shared)
