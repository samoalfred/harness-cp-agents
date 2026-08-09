"""
OpenAI client wrapper using the modern openai>=1.0 API.
"""

import os
from openai import OpenAI

_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable not set.")
        _client = OpenAI(api_key=api_key)
    return _client


def chat(messages, model="gpt-4o", temperature=0.1, max_tokens=4096):
    """
    Call the OpenAI Chat Completions API.

    Parameters
    ----------
    messages    : list of {"role": ..., "content": ...} dicts
    model       : model name string
    temperature : float
    max_tokens  : int

    Returns
    -------
    str  -- the assistant reply text
    """
    response = _get_client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()
