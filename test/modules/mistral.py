import os

def conversational_prompt(messages, system_prompt="You are a helpful assistant.", model="mistral-large-latest"):
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai python package is required for Mistral.")
    client = OpenAI(api_key=os.getenv("MISTRAL_API_KEY"), base_url="https://api.mistral.ai/v1")
    chat_messages = [{"role":"system","content":system_prompt}] + messages
    resp = client.chat.completions.create(model=model, messages=chat_messages)
    return resp.choices[0].message.content

def prefix_prompt(prompt, prefix="", model="mistral-large-latest"):
    # Trivial: just prepend prefix to user prompt and call as normal
    system_prompt = f"You must always begin your response with the following prefix: '{prefix}'.\n" if prefix else ""
    return conversational_prompt([{"role":"user","content":prompt}], system_prompt=system_prompt, model=model)