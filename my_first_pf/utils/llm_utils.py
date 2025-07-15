import os

from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def call_llm(prompt: str):
    response = client.responses.create(
        model="gpt-4o", input=[{"role": "user", "content": prompt}]
    )

    return response.output_text
