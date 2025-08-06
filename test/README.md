# "Always-On" Deepseek AI Assistant
> A pattern for an always on AI Assistant powered by Deepseek-V3, RealtimeSTT, and Typer for engineering
>
> Checkout [the demo](https://youtu.be/zoBwIi4ZiTA) where we walk through using this always-on-ai-assistant.

![ada-deepseek-v3.png](./images/ada-deepseek-v3.png)

## Setup
- `cp .env.sample .env`
  - Update with your keys `DEEPSEEK_API_KEY`, `ELEVEN_API_KEY`, `GEMINI_API_KEY`, `MISTRAL_API_KEY`, and `GROQ_API_KEY`
- `uv sync`
- (optional) install python 3.11 (`uv python install 3.11`)


## Commands

### Base Assistant Chat Interface
> See `main_base_assistant.py` for more details.
Start a conversational chat session with the base assistant:

```bash
uv run python main_base_assistant.py chat
```

### Typer Assistant Conversational Commands
> See `main_typer_assistant.py`, `modules/typer_agent.py`, and `commands/template.py` for more details.

- `--typer-file`: file containing typer commands
- `--scratchpad`: active memory for you and your assistant
- `--mode`: determines what the assistant does with the command: ('default', 'execute', 'execute-no-scratch').

1. Awaken the assistant
```bash
uv run python main_typer_assistant.py awaken --typer-file commands/template.py --scratchpad scratchpad.md --mode execute
# then say: "Ada, scan my network at 192.168.1.0/24 using common ports"
```

2. Speak to the assistant
Try this:
"Hello! Ada, ping the server wait for a response" (be sure to pronounce 'ada' clearly)

3. See the command in the scratchpad
Open `scratchpad.md` to see the command that was generated.

## Assistant Architecture
> See `assistant_config.yml` for more details.

### Typer Assistant
> See `assistant_config.yml` for more details.
- 🧠 Brain: Selectable! `deepseek-v3`, `gemini`, `mistral`, `groq`, `ollama:<model>`
- 📝 Job (Prompt(s)): `prompts/typer-commands.xml`
- 💻 Active Memory (Dynamic Variables): `scratchpad.txt`
- 👂 Ears (STT): `RealtimeSTT`
- 🎤 Mouth (TTS): `ElevenLabs`

### Base Assistant
> See `assistant_config.yml` for more details.
- 🧠 Brain: Selectable! `gemini` (default), `deepseek-v3`, `mistral`, `groq`, `ollama:<model>`
- 📝 Job (Prompt(s)): `None`
- 💻 Active Memory (Dynamic Variables): `none`
- 👂 Ears (STT): `RealtimeSTT`
- 🎤 Mouth (TTS): `ElevenLabs` (default)


## Resources
- LOCAL SPEECH TO TEXT: https://github.com/KoljaB/RealtimeSTT
- faster whisper (support for RealtimeSTT) https://github.com/SYSTRAN/faster-whisper
- whisper https://github.com/openai/whisper
- examples https://github.com/KoljaB/RealtimeSTT/blob/master/tests/realtimestt_speechendpoint_binary_classified.py
- elevenlabs voice models: https://elevenlabs.io/docs/developer-guides/models#older-models

- **LAN Scanner**: Trigger from voice or Typer using the `ip_port_scan` command.  
  Requires `gradio` to be installed.  
  Example CLI:
  ```bash
  uv run python main_typer_assistant.py awaken --typer-file commands/template.py --scratchpad scratchpad.md --mode execute
  # then say: "Ada, scan my network at 192.168.1.0/24 using common ports"
  ```

## Network Diagnostic Skills

You can now use these commands via Typer or voice:
- `network_ping` – Ping a host
- `network_traceroute` – Traceroute to a host
- `network_dns_lookup` – DNS lookup for a domain
- `network_port_scan` – TCP SYN port scan on a host
- `network_interface_info` – Show all network interface info (as JSON)
- `network_tcp_test` – Test TCP connection to a host/port

_Note: Requires `scapy`, `psutil`, `dnspython`, and `requests` in your Python environment._

## Text + Voice Chat

You can chat naturally in text (with TTS speech for replies) using:

```bash
uv run python commands/template.py chat
```

Type your messages and Ada will reply and speak.

_If ElevenLabs TTS is unavailable or fails, the assistant automatically falls back to local speech output._

**Voice example:**  
Say: “Ada, ping 8.8.8.8 three times”

## Gradio Web UI

Start the assistant's Web UI via CLI:

```bash
uv run python commands/template.py launch-webui --ip 0.0.0.0 --port 9000
```

_Note: Requires `browser-use`, `playwright`, `langchain-ollama`, and `pillow` for full Web UI functionality._

## Network Diagnostics

- `network_ping` — ping a host (`Ada, ping 8.8.8.8 three times`)
- `network_traceroute` — trace route to a host
- `network_dns_lookup` — resolve a DNS record
- `network_port_scan` — scan ports on a host
- `network_interface_info` — show interface info as JSON
- `network_tcp_test` — test TCP connection to host:port

You can invoke these via Typer or by saying the command in conversation.

## LLM Providers

You can now choose the AI "brain" for both the Typer Assistant and Base Assistant in `assistant_config.yml`:
- `deepseek-v3`
- `gemini` (Google Gemini, requires `GEMINI_API_KEY`)
- `mistral` (Mistral AI, requires `MISTRAL_API_KEY`)
- `groq` (Groq Cloud, requires `GROQ_API_KEY`)
- `ollama:<model>` (local models via Ollama, e.g., `ollama:phi4`)

Update your `.env` with the appropriate keys for your chosen provider.