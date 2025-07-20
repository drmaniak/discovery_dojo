import os
from typing import Type, TypeVar

from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


##### OPENAI UTILS ######
def call_llm(prompt: str, model: str = "gpt-4o", instructions: str = ""):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=[{"role": "user", "content": prompt}],
    )

    return response.output_text


def call_llm_structured(
    prompt, response_model: Type[T], model: str = "gpt-4o", instructions: str = ""
):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.responses.parse(
        model=model,
        instructions=instructions,
        input=[{"role": "user", "content": prompt}],
        text_format=response_model,  # type: ignore
    )
    return response.output_parsed


async def call_llm_async(prompt: str, model: str = "gpt-4o", instructions: str = ""):
    client_async = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = await client_async.responses.create(
        model=model,
        instructions=instructions,
        input=[{"role": "user", "content": prompt}],
    )

    return response.output_text


async def call_llm_structured_async(
    prompt: str,
    response_model: Type[T],
    model: str = "gpt-4o",
    instructions: str = "",
):
    client_async = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = await client_async.responses.parse(
        model=model,
        instructions=instructions,
        input=[{"role": "user", "content": prompt}],
        text_format=response_model,  # type: ignore
    )

    return response.output_text


##### NEBIUS UTILS ######


def call_embedder(query, model: str = "Qwen/Qwen3-Embedding-8B"):
    client = OpenAI(
        base_url="https://api.studio.nebius.com/v1/",
        api_key=os.environ.get("NEBIUS _API_KEY"),
    )

    response = client.embeddings.create(model=model, input=query)

    return response
