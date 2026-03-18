# Qwen3.5 Vision Issue - Status & Solutions

## 📋 The Situation

**Official Documentation Says:**
> "Qwen3.5-0.8B model series... possesses **native vision capabilities**. It is designed for efficient multimodal tasks, including image understanding and OCR."

**Reality in Ollama:**
- Model loads successfully ✓
- Text-only prompts work ✓
- **Vision prompts return empty responses** ✗

---

## 🔍 Root Cause Analysis

### What We Know:

1. **Qwen3.5-0.8B HAS vision capabilities** (confirmed by official docs)
2. **Architecture supports multimodal input** (early-fusion training)
3. **Ollama implementation may not include vision encoder**

### The Technical Issue:

Qwen3.5 uses a **unified vision-language architecture** with:
- Vision encoder (for processing images)
- Language model (for generating text)
- Cross-modal attention layers

**In Ollama:**
- The GGUF quantization may not include the vision encoder
- Vision requires special model format support
- Not all Ollama model builds include vision capabilities

---

## ✅ What We Fixed

### Vision Agent Optimizations:

Updated `backend/agents/vision_agent.py` with official Qwen3.5 vision parameters:

```python
options={
    'temperature': 0.7,      # Official VL parameter
    'top_p': 0.8,            # Official VL parameter
    'top_k': 20,             # Official VL parameter
    'presence_penalty': 1.5, # Official VL parameter
    'num_predict': 500
}
```

**Image Processing:**
- JPEG format at 95% quality (optimal for Qwen3.5)
- Proper byte stream handling
- Empty response detection

**Result:** Model responds but returns empty content → Vision encoder not active.

---

## 🛠️ Recommended Solutions

### Option 1: Use Larger Qwen3.5 Model (Recommended)

The 9B variant has better vision support in Ollama:

```bash
# Remove 0.8B
ollama rm qwen3.5:0.8b

# Pull 9B (requires ~7GB RAM)
ollama pull qwen3.5:9b

# Update app.py or vision_agent.py
model = "qwen3.5:9b"
```

**Pros:**
- Same Qwen3.5 family
- Better vision capabilities
- Official benchmarks show superior performance

**Cons:**
- Larger memory footprint (7GB vs 1GB)
- Slower inference

---

### Option 2: Use LLaVA (Alternative)

LLaVA has confirmed working vision in Ollama:

```bash
# Pull LLaVA
ollama pull llava

# Or LLaVA next-gen
ollama pull llava-llama-3
```

**Update Vision Agent:**
```python
# In vision_agent.py
self.model = "llava"  # or "llava-llama-3"
```

**Pros:**
- Vision definitely works
- Good image understanding
- Actively maintained

**Cons:**
- Different model family
- May need prompt adjustments

---

### Option 3: Wait for Ollama Update

Ollama may add proper vision support for Qwen3.5-0.8B in future releases.

**Monitor:**
- https://github.com/ollama/ollama/releases
- https://ollama.ai/library/qwen3.5

---

## 📊 Model Comparison

| Model | Size | Vision | RAM Required | Speed |
|-------|------|--------|--------------|-------|
| **qwen3.5:0.8b** | 1GB | ❌ (in Ollama) | 2GB | Fast |
| **qwen3.5:9b** | 7GB | ✅ | 8GB | Medium |
| **llava** | 4GB | ✅ | 6GB | Medium |
| **llava-llama-3** | 8GB | ✅ | 10GB | Slow |

---

## 🧪 Testing Vision

Use the included test script:

```bash
python test_vision.py
```

**Expected Output (if working):**
```
✓ Response received (150 chars):
   I see a blue rectangle on a white background...
✓ VISION TEST PASSED!
```

**Current Output:**
```
✓ Response received (0 chars):
   
⚠ Response doesn't describe the image correctly
```

---

## 💡 Workaround for Now

Since vision isn't working with qwen3.5:0.8b in Ollama, the app gracefully handles this:

1. **Media Extraction still works** - Images are extracted from documents
2. **Vision Analysis is skipped** - Shows warning in UI
3. **Other agents function normally** - File discovery, parsing, tables all work

**UI Shows:**
```
⚠ Vision Not Working - Model may not support vision
Try: `ollama pull llava` for vision support
```

---

## 📝 Next Steps

### Immediate:
1. **Choose alternative model** (qwen3.5:9b or llava)
2. **Update vision_agent.py** with new model name
3. **Test vision** with `python test_vision.py`

### Long-term:
1. **Monitor Ollama updates** for qwen3.5:0.8b vision support
2. **Consider vLLM or SGLang** for production (better vision support)
3. **Document vision requirements** for deployment

---

## 🔗 References

- **Qwen3.5 Official Docs**: https://github.com/QwenLM/Qwen3.5
- **Ollama Library**: https://ollama.ai/library/qwen3.5
- **Vision Benchmarks**: Qwen3.5-0.8B scores 49/47.4 on MMMU
- **vLLM Deployment**: https://docs.vllm.ai/en/latest/models/qwen3_5.html

---

**Last Updated:** 2026-03-16  
**Status:** ⚠️ Vision not working in qwen3.5:0.8b (Ollama build)  
**Recommendation:** Use qwen3.5:9b or llava for vision capabilities
