import sys
from os import PathLike
from pathlib import Path

from pocketflow import BatchFlow, Flow, Node
from utils.llm_utils import call_llm


# First node that acts as an
class LoadFiles(Node):
    def prep(self, shared):
        shared["folder"] = Path(shared["folder"])
        return shared["folder"]

    def exec(self, prep_res: Path):
        txt_files = prep_res.glob("*.txt")
        return txt_files

    def post(self, shared, prep_res, exec_res: list[Path]):
        shared["filepaths"] = exec_res


class FolderBatchFlow(BatchFlow):
    def prep(self, shared):
        return [{"filepath": fp} for fp in shared["filepaths"]]


class ReadFile(Node):
    def prep(self, shared):
        return Path(str(self.params["filepath"]))

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


# Per-File Flow
reader, lencheck, short_sum, long_sum, printer = (
    ReadFile(),
    DecideLength(),
    SummarizeShort(),
    SummarizeLong(),
    PrintResult(),
)

reader >> lencheck
lencheck - "long" >> long_sum
lencheck - "short" >> short_sum
short_sum >> printer
long_sum >> printer

per_file_flow = Flow(start=reader)

batch_flow = FolderBatchFlow(per_file_flow)

load_filepaths = LoadFiles()
load_filepaths >> batch_flow

main_flow = Flow(load_filepaths)
if __name__ == "__main__":
    shared = {"folder": sys.argv[1]}
    main_flow.run(shared)
