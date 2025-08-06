import os
import yaml
from dotenv import dotenv_values

ENV_KEYS = [
    "DEEPSEEK_API_KEY",
    "ELEVEN_API_KEY",
    "GEMINI_API_KEY",
    "MISTRAL_API_KEY",
    "GROQ_API_KEY"
]
ASSISTANT_CONFIG_PATH = "assistant_config.yml"

def load_env_keys():
    # Reads current .env (if present) and returns dict of keys
    config = {}
    if os.path.exists(".env"):
        config = dotenv_values(".env")
    return {k: config.get(k, "") for k in ENV_KEYS}

def save_env_keys(new_values):
    # Overwrites or appends key=value for each ENV_KEYS in .env
    existing = {}
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    existing[k] = v
    for k in ENV_KEYS:
        if k in new_values and new_values[k] != "":
            existing[k] = new_values[k]
    # Write back all values
    with open(".env", "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")

def load_assistant_config():
    # Reads YAML config and returns dict
    if not os.path.exists(ASSISTANT_CONFIG_PATH):
        return {}
    with open(ASSISTANT_CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
    return config

def save_assistant_config(new_config):
    # Overwrites YAML config
    with open(ASSISTANT_CONFIG_PATH, "w") as f:
        yaml.dump(new_config, f, default_flow_style=False)