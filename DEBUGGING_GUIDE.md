# SmartRenameAi - Debugging & Architecture Guide

## 1. MODEL DETAILS

### LLM Configuration
- **Model Name**: DeepSeek R1 8B (via Ollama)
- **Inference Engine**: Local Ollama API (`http://localhost:11434/api/generate`)
- **Temperature**: 0.0 (deterministic/greedy decoding)
- **Seed**: 42 (reproducible outputs)
- **Max Tokens**: 250 (allows thinking + output)
- **Timeout**: 15 seconds

### Vision Models
- **Image Classification**: EfficientNetB3 (ImageNet pre-trained)
  - Input size: 224×224
  - Output: Simplified category labels via mapping
  
- **Legacy Model** (not in use): MobileNetV2

### Audio Model
- **Feature Extraction**: Librosa
- **Sampling Rate**: 22,050 Hz
- **Duration**: First 10 seconds only
- **Features**: RMS, Zero-Crossing Rate, Spectral Centroid, Spectral Flatness

---

## 2. INPUT PIPELINE

### 2.1 File Reading
**Source**: [core/renamer.py](core/renamer.py) + [core/extractor.py](core/extractor.py)

```
File Input → Detect Type → Route to Appropriate Handler
```

### 2.2 Content Extraction

#### PDF Files
- **Extractor**: PyPDF2
- **Process**: Extract text from all pages, lowercase
- **Fallback**: Return empty string on error

#### DOCX Files
- **Method**: Parse as ZIP, extract from `word/document.xml`
- **Namespace**: OpenXML `http://schemas.openxmlformats.org/wordprocessingml/2006/main`
- **Output**: Concatenated text, lowercase

#### TXT Files
- **Method**: Direct file read with UTF-8 encoding, errors='ignore'
- **Output**: Lowercase text

#### Images
- **Extractor**: Tesseract OCR (if deep_mode=true)
- **Size Limits**: Defined but implementation varies

#### Video Frames
- **Method**: OpenCV frame extraction + histogram-based keyframe selection
- **Process**:
  1. Sample 9 candidate frames across video
  2. Calculate 3D color histogram for each
  3. Greedily select 3 most visually distinct frames
  4. Save to temp directory as JPG
  5. Classify each frame

#### Audio
- **Method**: FFmpeg extraction of first 10 seconds, convert to WAV 22.05kHz mono

### 2.3 Preprocessing Steps

1. **Security Check** (Pre-processing)
   - Calculate suspicion score via [core/security.py](core/security.py)
   - Quarantine high-risk files before any content access

2. **Hash-Based Caching** (Determinism)
   - SHA256 hash of first 10MB of file
   - Check `data/processed_memory.json` for cached result
   - Skip AI if file already processed

3. **Type Detection** → Route to handler

---

## 3. PROMPT(S) USED

### Document Classification Prompt
**File**: [core/classification/document.py](core/classification/document.py) line 37-61

```python
prompt = f"""You are a precise file naming assistant.
Read the document content below and output a descriptive filename (2-5 words, lowercase, underscores between words).
You MUST wrap your final suggested filename inside [FILENAME] and [/FILENAME] tags.

Examples:
  [FILENAME]invoice_microsoft_2024[/FILENAME]
  [FILENAME]resume_john_doe[/FILENAME]
  [FILENAME]meeting_notes_q3[/FILENAME]

DOCUMENT CONTENT:
{content}

Ensure your final suggested name is in the format [FILENAME]your_suggested_name[/FILENAME]:"""
```

**Characteristics**:
- Single-step prompt (no chain-of-thought in output)
- Requires `[FILENAME]...[/FILENAME]` tag wrapping
- Content truncated to first 2000 chars
- Examples provide context
- Output: 2-5 words, lowercase, underscores

### Image Classification
**No prompt** — Uses pre-trained EfficientNetB3 + label mapping

### Audio Classification
**No prompt** — Uses feature-based heuristics (not ML)

### Video Classification
**No prompt** — Merges visual + audio predictions via rules

---

## 4. OUTPUT HANDLING

### 4.1 LLM Output Processing

**Function**: `clean_ai_label()` in [core/classification/document.py](core/classification/document.py)

```python
def clean_ai_label(text: str) -> str:
    # 1. Strip <think>...</think> tags (DeepSeek R1 chain-of-thought)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # 2. Extract content inside [FILENAME]...[/FILENAME] tags
    match = re.search(r'\[FILENAME\](.*?)\[/FILENAME\]', text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        text = match.group(1)
    
    # 3. Lowercase + remove filler phrases
    text = text.lower().strip()
    for phrase in ["the filename is", "filename:", "here is", "answer:", "output:"]:
        text = text.replace(phrase, "")
    
    # 4. Remove non-alphanumeric except underscores and spaces
    text = re.sub(r'[^a-z0-9_\s]', '', text)
    
    # 5. Normalize whitespace → underscores
    text = re.sub(r'\s+', '_', text)
    text = re.sub(r'_+', '_', text)  # Remove duplicate underscores
    
    return text.strip("_")
```

### 4.2 Filename Generation

**Location**: [core/renamer.py](core/renamer.py) lines 170-210

**Pipeline**:
```
AI Output → clean_ai_label() → sanitize_ai_output() → Validation
  ↓
[Validation]:
  - Check if >= 3 chars
  - Check if not all digits
  - Apply STOP_WORDS filter (config.py)
  - Limit to first 5 words after dedup
  ↓
new_name = f"{file_type}_{ai_name}{ext}"
```

**Fallback Chain**:
1. Use AI output (if valid)
2. Clean original filename (if AI fails)
3. Default to "unnamed_file" (if all fail)

### 4.3 Final Filename Structure

```
<file_type>_<ai_name><extension>

Examples:
- document_invoice_microsoft_2024.pdf
- image_dog_playing.jpg
- video_tutorial_python.mp4
```

---

## 5. CURRENT ISSUES & EXAMPLES

### Issue 1: LLM Sometimes Outputs Explanations Instead of Filenames
**Symptom**: Filename like `thefile_isapdfwith_informationabout_...`

**Root Cause**: LLM not strictly following `[FILENAME]...[/FILENAME]` tag instruction

**Example**:
```
LLM Output: "The filename is [FILENAME]invoice_2024[/FILENAME]. This is a business document."
Clean Output: "the_filename_is_invoice_2024_this_is_a_business_document"
Result: WRONG (extra filler text included)
```

**Fix Attempted**: `clean_ai_label()` extracts between tags, but if tags missing → entire output used

---

### Issue 2: Stop Words Filtering Too Aggressive
**Symptom**: Useful words removed ("financial_report" → "report")

**Location**: config.py line 27

**Current STOP_WORDS**:
```python
{"this", "is", "a", "an", "the", "appears", "to", "be", "of", "for", "and", "in", "on", "with", "it", "that", "there", "some", "here", "are"}
```

**Example**:
```
LLM: "financial report"
After stop word filter: "report" (loses context)
```

---

### Issue 3: Content Truncation (2000 chars) Loses Context
**Location**: [core/classification/document.py](core/classification/document.py) line 49

**Problem**: Large documents (contracts, books) only first 2000 chars sent to LLM

**Example**:
```
50-page contract → Only first 2000 chars → Missing key clauses
Result: Generic filename like "document_content" instead of "contract_nda_2024"
```

---

### Issue 4: Image Classification Simplified Labels Too Generic
**Location**: [core/classification/image.py](core/classification/image.py) line 45-98

**Problem**: ImageNet outputs mapped to generic categories

**Example**:
```
ImageNet: "Pembroke Welsh Corgi"
Simplified: "dog"
Result: "image_dog.jpg" (loses breed/detail)
```

---

### Issue 5: No Validation that Filename is Actually Descriptive
**Symptom**: Random words passed through ("image_qwerty_asdf")

**Location**: [core/renamer.py](core/renamer.py) lines 198-202

**Current Check**: Only validates >= 3 chars + not all digits

**Missing**: 
- Check if words are real English words
- Check if filename makes semantic sense
- Confidence score threshold

---

### Issue 6: Cache Determinism is File-Based, Not Content-Based
**Problem**: If file modified (same name, different content) → cached old name used

**Location**: [core/renamer.py](core/renamer.py) lines 170-175

```python
file_hash = get_file_hash(file_path)  # Only hashes file content
memory = load_memory()
if file_hash and file_hash in memory:
    return memory[file_hash]  # ← Returns cached name, ignoring current content
```

---

## 6. CODE SNIPPETS - CRITICAL PATHS

### 6.1 Main Rename Pipeline
**File**: [core/renamer.py](core/renamer.py) lines 160-210

```python
def rename_file(file_path, deep_mode=True, output_base=OUTPUT_BASE):
    try:
        # 1. SECURITY SCAN
        score, level, remarks, mime = calculate_suspicion(file_path)
        if level in ["High", "Critical", "Medium"]:
            return f"quarantined_{clean_text(name)}{ext}"

        # 2. DETERMINISM CHECK (Cache by file hash)
        file_hash = get_file_hash(file_path)
        memory = load_memory()
        if file_hash and file_hash in memory:
            return memory[file_hash]

        # 3. CONTENT CLASSIFICATION - Route by type
        file_type = detect_file_type(file_path)

        if file_type == "image":
            ai_name = classify_image(file_path, deep_mode=deep_mode)
        elif file_type == "audio":
            ai_name = classify_audio(file_path, deep_mode=deep_mode)
        elif file_type == "video":
            ai_name = classify_video(file_path, deep_mode=deep_mode)
        elif file_type == "document":
            ai_name = classify_document(file_path, deep_mode=deep_mode)
        else:
            ai_name = clean_text(name)

        # 4. SANITIZE & VALIDATE
        ai_name = sanitize_ai_output(ai_name)
        if not ai_name or len(ai_name) < 3:
            ai_name = clean_text(name) or "unnamed_file"

        new_name = f"{file_type}_{ai_name}{ext}"
        
        # 5. SAVE TO CACHE
        if file_hash:
            memory[file_hash] = new_name
            save_memory(memory)

        return new_name

    except Exception as e:
        logger.error(f"❌ Rename Error: {e}", exc_info=True)
        return os.path.basename(file_path)
```

---

### 6.2 LLM API Call
**File**: [core/classification/document.py](core/classification/document.py) lines 48-67

```python
def classify_document_text(content: str) -> str:
    try:
        content = str(content)[:2000]  # ← TRUNCATION ISSUE
        prompt = f"""You are a precise file naming assistant..."""

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-r1:8b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,      # ← Deterministic
                    "seed": 42,              # ← Reproducible
                    "num_predict": 250,      # ← Allow thinking + output
                }
            },
            timeout=15
        )

        result = response.json()
        text = result.get("response", "").strip()
        text = clean_ai_label(text)

        if text and len(text) >= 3 and not text.isdigit():
            return text

        return ""  # ← Fallback to original filename

    except Exception as e:
        logger.error(f"⚠️ LLM Error: {e}")
        return ""
```

---

### 6.3 Output Sanitization
**File**: [core/renamer.py](core/renamer.py) lines 80-110

```python
def sanitize_ai_output(text: str) -> str:
    # 1. Strip thinking tags
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    # 2. Lowercase
    text = text.lower()

    # 3. Remove file extensions
    text = re.sub(
        r'\.(txt|pdf|jpg|jpeg|png|ppt|pptx|doc|docx|mp4|mkv)',
        '',
        text
    )

    # 4. Remove non-alphanumeric
    text = re.sub(r'[^a-z0-9_\s]', '', text)
    
    # 5. Normalize spaces → underscores
    text = re.sub(r'\s+', '_', text)
    text = re.sub(r'_+', '_', text)

    # 6. Remove STOP_WORDS and duplicates, limit to 5 words
    words = text.split("_")
    cleaned = []
    for w in words:
        if w and w not in STOP_WORDS and w not in cleaned:
            cleaned.append(w)

    text = "_".join(cleaned[:5])

    # 7. Fallback if empty or too short
    if not text or len(text) < 3:
        return "unnamed_file"

    return text.strip("_")
```

---

### 6.4 Image Classification Pipeline
**File**: [core/classification/image.py](core/classification/image.py) lines 95-145

```python
def classify_image(img_path):
    from core.mode_manager import get_current_mode
    if get_current_mode() == "online":
        # TODO: route to cloud API
        return "image"
        
    try:
        model, _preprocess, _decode, _load_img, _img_to_array = load_tf()

        img = _load_img(img_path, target_size=(224, 224))
        x = _img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = _preprocess(x)

        preds = model.predict(x, verbose=0)
        label = _decode(preds, top=1)[0][0][1]  # Top-1 prediction

        simplified = simplify_imagenet_label(label)
        return simplified.lower()

    except Exception as e:
        print(f"⚠️ Image AI Error: {e}")
        return "image"
```

---

### 6.5 Video Classification - Keyframe Selection
**File**: [core/classification/video.py](core/classification/video.py) lines 26-60

```python
# Sample 9 candidates across video
candidate_ratios = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
candidate_indices = [int(total_frames * r) for r in candidate_ratios]

# Greedy selection: pick most visually distinct frames
selected_idx = [0]
while len(selected_idx) < 3 and len(selected_idx) < len(frames_data):
    best_candidate_idx = -1
    min_similarity = 1.0
    for i, cand in enumerate(frames_data):
        if i in selected_idx:
            continue
        max_sim_to_selected = max(
            cv2.compareHist(cand[2], frames_data[s][2], cv2.HISTCMP_CORREL) 
            for s in selected_idx
        )
        if max_sim_to_selected < min_similarity:
            min_similarity = max_sim_to_selected
            best_candidate_idx = i
    if best_candidate_idx != -1:
        selected_idx.append(best_candidate_idx)
```

---

### 6.6 Audio Classification - Feature-Based Heuristics
**File**: [core/classification/audio.py](core/classification/audio.py) lines 18-62

```python
def classify_audio(file_path, deep_mode=True):
    try:
        import librosa, numpy as np
        
        y, sr = librosa.load(safe_path, duration=10, sr=22050)  # First 10s only
        
        # Extract features
        rms = librosa.feature.rms(y=y)
        zcr = librosa.feature.zero_crossing_rate(y)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        flatness = librosa.feature.spectral_flatness(y=y)
        
        mean_rms = float(np.mean(rms))
        std_rms = float(np.std(rms))
        mean_zcr = float(np.mean(zcr))
        mean_centroid = float(np.mean(centroid))
        mean_flatness = float(np.mean(flatness))
        
        # Decision tree:
        if mean_rms < 0.005:
            return "quiet_audio"
        
        rms_var_coeff = std_rms / (mean_rms + 1e-6)
        
        if mean_zcr > 0.13 or (mean_zcr > 0.08 and rms_var_coeff > 0.5 and mean_centroid > 1500):
            return "speech_recording"
        elif mean_rms > 0.02:
            try:
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                tempo_val = float(tempo[0]) if isinstance(tempo, (np.ndarray, list)) else float(tempo)
            except:
                tempo_val = 60.0
            
            if mean_flatness > 0.05 and mean_zcr > 0.15:
                return "ambient_noise"
            elif tempo_val > 50:
                return "music_track"
            else:
                return "ambient_noise"
        else:
            return "ambient_noise"
    except Exception as e:
        print(f"⚠️ Audio Classification Error: {e}")
        return "audio_file"
```

---

## 7. SUMMARY TABLE

| Component | Technology | Status | Issue |
|-----------|-----------|--------|-------|
| **LLM** | DeepSeek R1 8B (Ollama) | Working | Sometimes ignores `[FILENAME]` tags |
| **Vision** | EfficientNetB3 | Working | Labels too generic (needs fine-tuning) |
| **Audio** | Librosa heuristics | Working | Limited accuracy, no ML model |
| **Video** | OpenCV + keyframe selection | Working | Audio extraction requires FFmpeg |
| **Text Extraction** | PyPDF2, zipfile, librosa | Working | 2000 char truncation loses context |
| **Caching** | SHA256 memory.json | Working | File-based, not content-aware |
| **Stop Words** | Static list | Issue | Too aggressive filtering |
| **Validation** | Minimal (3 chars + not digits) | Issue | No semantic validation |

---

## 8. DEBUG CHECKLIST

- [ ] Verify Ollama running: `curl http://localhost:11434/api/tags`
- [ ] Check cache: `cat data/processed_memory.json`
- [ ] Monitor LLM output: Add logging to `clean_ai_label()` 
- [ ] Test specific file: Run `python main.py /path/to/file`
- [ ] Check logs: `tail -f logs/log.txt`
- [ ] Validate prompt: Print `content[:2000]` before sending to LLM
- [ ] Test fallbacks: Disable LLM, see if `clean_text(name)` works
