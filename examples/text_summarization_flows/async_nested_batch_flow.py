import asyncio
from os import PathLike
from pathlib import Path
from typing import Any

import aiofiles
from pocketflow import AsyncFlow, AsyncNode, AsyncParallelBatchFlow, Node
from utils.llm_utils import call_llm_async


# First node that acts as an
class FolderBatchFlow(AsyncParallelBatchFlow):
    async def prep_async(self, shared):
        folders = shared["folders"]
        assert isinstance(folders, list), (
            f"Error: Expected folders to be a list, received {type(folders)}"
        )

        return [{"folder": f} for f in folders]


class LoadFiles(AsyncNode):
    async def prep_async(self, shared):
        return Path(str(self.params["folder"]))

    async def exec_async(self, prep_res: Path):
        txt_files = prep_res.glob("*.txt")
        return txt_files

    async def post_async(self, shared, prep_res, exec_res: list[Path]):
        shared["filepaths"] = exec_res


class FileBatchFlow(AsyncParallelBatchFlow):
    async def prep_async(self, shared):
        return [{"filepath": fp} for fp in shared["filepaths"]]


class ReadFile(AsyncNode):
    async def prep_async(self, shared):
        return Path(str(self.params["filepath"]))

    async def exec_async(self, prep_res: PathLike):
        async with aiofiles.open(prep_res, "r") as f:
            return await f.read()

    async def post_async(self, shared, prep_res, exec_res: str):
        shared["raw"] = exec_res


class DecideLength(Node):
    def prep(self, shared):
        return shared["raw"]

    def exec(self, prep_res: str):
        str_len = len(prep_res.replace("\n", "").replace(" ", ""))
        length: str = ""
        if str_len > 1000:
            print(f"\nLong text detected with {str_len} characters")
            length = "long"
        else:
            print(f"\nShort text detected with {str_len} characters")
            length = "short"

        return length

    def post(self, shared, prep_res, exec_res: int):
        shared["length"] = exec_res
        return shared["length"]


class SummarizeShort(AsyncNode):
    async def prep_async(self, shared):
        return shared["raw"]

    async def exec_async(self, prep_res: str):
        prompt = f"Summarize in exactly 10 words: {prep_res}"
        return await call_llm_async(prompt)

    async def post_async(self, shared, prep_res, exec_res):
        shared["summary"] = exec_res


class SummarizeLong(SummarizeShort):
    async def exec_async(self, prep_res: str):
        prompt = f"Summarize in exactly 50 words: {prep_res}"
        return await call_llm_async(prompt)


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

# File Read Flow
reader >> lencheck
lencheck - "long" >> long_sum
lencheck - "short" >> short_sum
short_sum >> printer
long_sum >> printer

per_file_flow = AsyncFlow(start=reader)

# Inner Batch Flow
file_batch_flow = FileBatchFlow(per_file_flow)

load_filepaths = LoadFiles()
load_filepaths >> file_batch_flow

# Outer Batch Flow
folder_batch_flow = FolderBatchFlow(load_filepaths)


async def main(shared: dict[str, Any]):
    await folder_batch_flow.run_async(shared)


if __name__ == "__main__":
    shared = {"folders": ["texts", "texts2"]}
    asyncio.run(main(shared))
