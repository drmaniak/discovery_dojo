import os

from openai import OpenAI
from pydantic import BaseModel

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def call_llm(prompt: str):
    response = client.responses.create(
        model="gpt-4o", input=[{"role": "user", "content": prompt}]
    )

    return response.output_text


def call_llm_structured(prompt, response_model: BaseModel):
    response = client.responses.parse(
        input=[{"role": "user", "content": prompt}],
        text_format=response_model,  # type: ignore
    )
    return response.output_parsed
