import os

def conversational_prompt(messages, system_prompt="You are a helpful assistant.", model="llama3-70b-8192"):
    try:
        from groq import Groq
    except ImportError:
        raise ImportError("groq python package is required for Groq Cloud.")
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    chat_messages = [{"role":"system","content":system_prompt}] + messages
    resp = client.chat.completions.create(model=model, messages=chat_messages)
    return resp.choices[0].message.content

def prefix_prompt(prompt, prefix="", model="llama3-70b-8192"):
    # Trivial: just prepend prefix to user prompt and call as normal
    system_prompt = f"You must always begin your response with the following prefix: '{prefix}'.\n" if prefix else ""
    return conversational_prompt([{"role":"user","content":prompt}], system_prompt=system_prompt, model=model)