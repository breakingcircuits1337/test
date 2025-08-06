import os

def conversational_prompt(messages, system_prompt="You are a helpful assistant.", model="gemini-1.0-pro-latest"):
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("google-generativeai is not installed. Please install it to use Gemini.")
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    joined = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    full_prompt = f"{system_prompt}\n{joined}"
    model_obj = genai.GenerativeModel(model)
    resp = model_obj.generate_content(full_prompt)
    return resp.text

def prefix_prompt(prompt, prefix="", model="gemini-1.0-pro-latest"):
    # Trivial: prepend prefix and ask model to complete
    system_prompt = f"You must always begin your response with the following prefix: '{prefix}'.\n" if prefix else ""
    return conversational_prompt([{"role":"user","content":prompt}], system_prompt=system_prompt, model=model)