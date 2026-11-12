$ErrorActionPreference = "Continue"

$modelDir = "D:\llm\models\qwen3.8-27b-mix"
$llamaDir = "D:\llm\llama.cpp-vulkan"
$logDir = "D:\llm\logs"
New-Item -ItemType Directory -Force $logDir | Out-Null

& "$llamaDir\llama-server.exe" `
  -m "$modelDir\Qwen3.8-27B-IQ3-MIX.gguf" `
  --alias qwen3.8-27b-forensics `
  --host 127.0.0.1 --port 8095 `
  --api-key-file "D:\llm\secrets\llama.key" `
  -c 65536 -np 1 -ngl 64 `
  -b 512 -ub 128 -t 6 -tb 6 `
  --fit off --jinja --flash-attn on `
  --cache-type-k q8_0 --cache-type-v q8_0 `
  --kv-unified --cache-ram 512 `
  --reasoning off `
  --offline --no-webui --metrics `
  *>> "$logDir\llama-27b-iq3-vulkan-64.log"
