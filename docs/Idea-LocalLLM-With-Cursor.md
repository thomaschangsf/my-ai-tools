Here is a concise, step-by-step guide you can paste into your notes or share.

---

# 🚀 Guide: Connecting Cursor to LM Studio
### -1 : TLDR

```bash
# Start up LM Studio daemon + backend
lms daemon up

lms unload google/gemma-3-4b
lms load google/gemma-3-4b
# or go to AI studio --> model --> load tab on right --> slider
lms load google/gemma-3-4b --context-length 126818
lms server start --port 1234


# use cloud to open http to local port
brew install cloudflared
cloudflared tunnel --url http://localhost:1234 2>&1 | tee /tmp/cf-tunnel.log
export TUNNEL_URL=$(grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' /tmp/cf-tunnel.log | head -1)
echo "Cursor base URL: $TUNNEL_URL/v1"
   
curl -i "${TUNNEL_URL}/v1/models"

curl -i "${TUNNEL_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer lm-studio" \
  -d '{
    "model": "google/gemma-3-4b",
    "messages": [{"role":"user","content":"Say hello in 5 words"}],
    "temperature": 0
  }'

# Streaming request
curl -sS -N -X POST "$TUNNEL_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer lm-studio" \
  -d '{"model":"google/gemma-3-4b","messages":[{"role":"user","content":"Hi"}],"max_tokens":20,"stream":true}'

# ------------------------------
# Update Cursor settings
# ------------------------------
Open Cursor and go to **Settings** (`Cmd/Ctrl + Shift + J`) > **Models**:

# add model id you see here ${TUNNEL_URL}/v1/vmodels
# ie: google/gemma-3-4b

# Open API Key: lm-studio

# Override open base url: echo $TUNNEL_URL
https://elwood-unpermissive-leoma.ngrok-free.dev/v1

When using cursor chat: 
1. Change model to google/gemma-3b

If something goes wrong, look at lm-studio logs
```


### 0: Setup LM Studio
```commandline

# -----------------
# Download LM Studio Mac APp
# -----------------
curl -fsSL https://lmstudio.ai/install.sh | bash
lms --help


# -----------------
# Python
# -----------------
pip install lmstudio
import lmstudio as lms

with lms.Client() as client:
    model = client.llm.model("openai/gpt-oss-20b")
    result = model.respond("Who are you, and what can you do?")
    print(result)

# Smoke Test

lms daemon up          # Start the daemon
lms get <model>        # Download a model
lms server start       # Start the local server
lms chat               # Open an interactive session

lms ps                 # List models currently stored into memory

```

- Test
```bash
google/gemma-3-4b 
lms server start --port 1234

curl http://localhost:1234/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LM_API_TOKEN" \
  -d '{
    "model": "google/gemma-3-4b",
    "input": "Who are you, and what can you do?"
  }'

```

### 1. Start LM Studio Server

* **Load Model:** Load your preferred model (e.g., `Qwen2.5-Coder`). [lmstudio download](https://lmstudio.ai/download)
* **Start Server:** Go to the **Local Server** tab and click **Start Server**.
* **Port:** Ensure it is running on port `1234`.
* **CORS:** Toggle **CORS** to `ON` in the server settings.

### 2. Create a Public Tunnel (Required)

Cursor requires an `https` endpoint to communicate with its backend. Use **ngrok** to expose your local port:

* Run the following in your terminal:
```bash
brew install ngrok
ngrok config add-authtoken 39u673BUKTNFQ3LgNn4DfJmfYeH_ZochggrNxSbfzqvQJoXR

ngrok http 1234

```


* **Copy the URL:** Look for the `Forwarding` address (e.g., `https://xxxx-xxxx.ngrok-free.app`).

### 3. Configure Cursor Settings

Open Cursor and go to **Settings** (`Cmd/Ctrl + Shift + J`) > **Models**:

* **OpenAI API Key:** Enter `lm-studio` (or any text).
* **Override OpenAI Base URL:** Paste your ngrok URL and add `/v1` (e.g., `https://xxxx.ngrok-free.app/v1`).
* **Add Custom Model:** 1. Click **+ Add Model**.
2. Enter the **exact model identifier** from LM Studio (found in the server logs/header).
* **Toggle Models:** Turn **OFF** all default models and turn **ON** only your custom local model.

---

### 💡 Quick Verification

Check the **LM Studio Logs**. If the connection is successful, you will see a `POST /v1/chat/completions` request appear the moment you type a prompt in Cursor's chat.

