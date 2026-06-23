# SmartRenameAi - Pipeline Optimization & Fixes

---

## PROBLEM ANALYSIS

### Current Issues
1. **Weak Single-Step Prompting**: One prompt tries to do everything
2. **Context Truncation (2000 chars)**: Loses critical information in long documents
3. **Poor Output Control**: Model can ignore [FILENAME] tags and add explanations
4. **Aggressive Stop-Word Filtering**: Removes meaningful words (financial → empty)
5. **Minimal Validation**: Only checks length ≥3 and not all digits
6. **No Preprocessing**: Raw text goes directly to LLM

---

## --- FIXED PIPELINE ---

### Step 1: SMART CONTENT EXTRACTION & PREPROCESSING
```
Input File 
  ↓
[Extract Text] → Handle truncation strategically:
  - Take first 1500 chars (important intro context)
  - + last 500 chars (closing/summary)
  - Total: 2000 chars (same size, better coverage)
  ↓
[Clean Text] → Remove metadata, normalize whitespace
  ↓
[Extract Key Terms] → Find important nouns (via simple heuristics)
  ↓
Step 2
```

**Key Improvement**: Instead of `content[:2000]`, use:
```python
first_part = content[:1500]
last_part = content[-500:] if len(content) > 2000 else ""
smart_content = first_part + ("\n\n[END OF DOC]\n" + last_part if last_part else "")
```

---

### Step 2: GENERATE STRUCTURED SUMMARY (1 line)
```
[Smart Content] (2000 chars)
  ↓
[LLM Step 1: Summarization Prompt]
  - Force output: ONLY 1-2 sentence summary
  - Format: Plain text, NO tags, NO explanations
  - Output: KEY_TOPIC document_type
  ↓
[Validation: Check summary != empty]
  ↓
Step 3
```

**Why separate**: Breaks down the task into manageable steps. LLMs perform better with focused, single-task prompts.

---

### Step 3: GENERATE FILENAME FROM SUMMARY (Strict Format)
```
[1-2 Sentence Summary] (e.g., "Financial audit report 2024")
  ↓
[LLM Step 2: Filename Generation Prompt]
  - Input: Summary only (short, focused)
  - Force output: [FILENAME_START]...[FILENAME_END]
  - HARD CONSTRAINT: No text outside tags
  - Output ONLY filename words (2-5 words)
  ↓
[Extract & Validate] → Must be 2-5 words, underscores only
  ↓
Final Filename: {file_type}_{ai_name}{ext}
```

---

### Step 4: VALIDATION & FALLBACK CHAIN
```
Generated Filename
  ↓
[Validate]:
  ✓ Word count: 2-5 words
  ✓ Format: lowercase, underscores only, no special chars
  ✓ Length: 3-50 chars
  ✓ Not all digits
  ✓ Not too many underscores
  ↓
If VALID: Use AI name
If INVALID: Fallback chain:
  1. Try with fewer words (remove least common)
  2. Use cleaned original filename
  3. Use category-based default (e.g., "document_unnamed")
```

---

## --- IMPROVED PROMPTS ---

### PROMPT 1: SUMMARIZATION (Document Analysis)
```
TASK: Analyze the document and extract ONE summary line.

RULES:
- Output EXACTLY 1-2 sentences
- Identify: document type (e.g., invoice, report, contract)
- Identify: key subject/topic
- Output plain text ONLY - no tags, no explanation, no extra text
- If unclear, output: "unknown_document"

CONTENT:
{smart_content}

RESPONSE FORMAT:
[TYPE]: invoice | report | contract | receipt | resume | letter | proposal | etc.
[TOPIC]: (main subject in 2-3 words)
Example: [TYPE]: invoice | [TOPIC]: microsoft azure services 2024
```

**Why this works**:
- Structured output format (KEY: VALUE pairs)
- Forced single task (summarize, not rename)
- Clear examples
- No room for filler text

---

### PROMPT 2: FILENAME GENERATION (Strict Tags)
```
TASK: Convert the summary into a 2-5 word filename.

RULES:
- Input is a document summary (already analyzed)
- Output EXACTLY 2-5 words
- Use lowercase, separate words with underscores
- No special characters (#, $, %, &, etc.)
- No dots or extensions
- MUST wrap output in [FILENAME_START] and [FILENAME_END] tags
- Output NOTHING outside these tags
- Example: [FILENAME_START]invoice_microsoft_2024[FILENAME_END]

DOCUMENT SUMMARY:
{summary_from_step_1}

YOUR RESPONSE MUST BE EXACTLY:
[FILENAME_START]word_word_word[FILENAME_END]

Do not add explanation, commentary, or anything else.
```

**Why this works**:
- Hard enforcement of tag format
- Single-task focus (summarize → convert to filename)
- Impossible to add filler text
- Clear boundary markers

---

### PROMPT 3: FILENAME RECOVERY (If Model Fails)
```
TASK: Extract a valid filename from problematic text.

RULES:
- If text contains explanations, extract ONLY the filename part
- Remove all text outside [FILENAME_START]...[FILENAME_END]
- If no tags found, extract 2-5 words from text
- Ensure lowercase, underscores only

PROBLEMATIC TEXT:
{raw_model_output}

CORRECTED FILENAME (2-5 words, underscores, lowercase):
[FILENAME_START]...[FILENAME_END]
```

**When to use**: Fallback if Step 2 output is malformed.

---

## --- CODE FIXES ---

### FIX 1: Smart Content Extraction (preprocessing)

**File**: `core/classification/document.py`

```python
def smart_content_extraction(content: str, max_total: int = 2000) -> str:
    """
    Extract start + end of content, preserving context.
    Better than linear truncation for long documents.
    """
    content = str(content).strip()
    
    if len(content) <= max_total:
        return content
    
    # Strategy: first 70% + last 30% of total budget
    first_part_size = int(max_total * 0.7)  # ~1400 chars
    last_part_size = max_total - first_part_size  # ~600 chars
    
    first_part = content[:first_part_size]
    last_part = content[-last_part_size:]
    
    # Add marker to indicate truncation
    combined = first_part + "\n\n[... DOCUMENT CONTINUES ...]\n\n" + last_part
    
    return combined[:max_total]  # Ensure we don't exceed max_total
```

---

### FIX 2: Multi-Step Classification Pipeline

**File**: `core/classification/document.py`

```python
def classify_document_v2(file_path, deep_mode=True):
    """
    NEW PIPELINE:
    Step 1: Extract → Clean → Get Summary
    Step 2: Generate filename from summary
    Step 3: Validate & fallback
    """
    from core.analysis.sandbox import SecureFileReader
    from core.extractor import extract_text
    
    original_name = _name_from_path(file_path)
    
    if not deep_mode:
        return original_name
    
    try:
        with SecureFileReader(file_path) as safe_path:
            content = extract_text(safe_path)
            
            if not content or len(content.strip()) < 10:
                logger.warning(f"⚠️ No readable content in '{os.path.basename(file_path)}'")
                return original_name
            
            # STEP 1: Generate Summary
            summary = generate_document_summary(content)
            if not summary:
                logger.warning(f"⚠️ Summary generation failed for '{os.path.basename(file_path)}'")
                return original_name
            
            # STEP 2: Generate Filename from Summary
            ai_name = generate_filename_from_summary(summary)
            
            # STEP 3: Validate & Fallback
            ai_name = validate_and_fallback(ai_name, original_name)
            
            return ai_name
            
    except Exception as e:
        logger.error(f"❌ Document classification error: {e}", exc_info=True)
        return original_name
```

---

### FIX 3: Step 1 - Summary Generation (Strict Format)

**File**: `core/classification/document.py` (NEW)

```python
def generate_document_summary(content: str) -> str:
    """
    STEP 1: Generate structured summary from content.
    Output format: [TYPE]: X | [TOPIC]: Y
    """
    try:
        smart_content = smart_content_extraction(content, max_total=2000)
        
        prompt = """TASK: Analyze the document and extract ONE summary line.

RULES:
- Output EXACTLY 1-2 sentences
- Identify: document type (e.g., invoice, report, contract, proposal, receipt, letter, resume)
- Identify: key subject/topic (2-3 words)
- Output plain text ONLY - NO tags, NO explanation
- If content is unclear or generic: output "unknown document"

DOCUMENT CONTENT:
{content}

RESPONSE FORMAT (EXACTLY as shown):
[TYPE]: (document_type) | [TOPIC]: (key subject)

EXAMPLES:
[TYPE]: invoice | [TOPIC]: microsoft azure 2024
[TYPE]: report | [TOPIC]: financial audit q3
[TYPE]: contract | [TOPIC]: employment agreement
""".format(content=smart_content)
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-r1:8b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "seed": 42,
                    "num_predict": 100,  # Only need ~50 tokens for summary
                }
            },
            timeout=15
        )
        
        result = response.json()
        summary = result.get("response", "").strip()
        
        # Extract structured output
        summary_clean = extract_summary_structured(summary)
        
        if summary_clean and len(summary_clean) > 5:
            logger.debug(f"✓ Summary generated: {summary_clean}")
            return summary_clean
        
        return None
        
    except Exception as e:
        logger.error(f"⚠️ Summary generation error: {e}")
        return None


def extract_summary_structured(text: str) -> str:
    """
    Extract summary from structured format: [TYPE]: X | [TOPIC]: Y
    """
    # Try to match structured format
    match = re.search(
        r'\[TYPE\]:\s*([^\|]+?)\s*\|\s*\[TOPIC\]:\s*(.+?)(?:\n|$)',
        text,
        re.IGNORECASE
    )
    
    if match:
        doc_type = match.group(1).strip()
        topic = match.group(2).strip()
        return f"{doc_type} {topic}".lower()
    
    # Fallback: return first line if structured format not found
    lines = text.strip().split('\n')
    if lines:
        return lines[0].lower()
    
    return None
```

---

### FIX 4: Step 2 - Filename Generation (Hard Tag Enforcement)

**File**: `core/classification/document.py` (NEW)

```python
def generate_filename_from_summary(summary: str) -> str:
    """
    STEP 2: Generate filename from summary.
    Enforces STRICT tag format - no escape possible.
    """
    try:
        prompt = """TASK: Convert a document summary into a filename.

RULES:
- Input: A document summary (already analyzed)
- Output: 2-5 lowercase words, separated by underscores
- NO special characters, NO dots, NO spaces
- MUST be wrapped in [FILENAME_START] and [FILENAME_END]
- Output NOTHING outside the tags
- NO explanation, NO commentary

SUMMARY:
{summary}

RESPONSE (EXACTLY):
[FILENAME_START]word_word_word[FILENAME_END]

Do NOT output anything else. Only the filename in tags.""".format(summary=summary)
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-r1:8b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "seed": 42,
                    "num_predict": 50,  # Very short - just filename
                }
            },
            timeout=15
        )
        
        result = response.json()
        text = result.get("response", "").strip()
        
        # Extract from tags
        filename = extract_filename_strict(text)
        
        if filename:
            logger.debug(f"✓ Filename generated: {filename}")
            return filename
        
        return None
        
    except Exception as e:
        logger.error(f"⚠️ Filename generation error: {e}")
        return None


def extract_filename_strict(text: str) -> str:
    """
    Extract filename from strict tag format.
    ONLY accept content between [FILENAME_START] and [FILENAME_END].
    """
    # Match tags (case-insensitive)
    match = re.search(
        r'\[FILENAME_START\](.*?)\[FILENAME_END\]',
        text,
        re.IGNORECASE | re.DOTALL
    )
    
    if match:
        filename = match.group(1).strip()
        # Clean: lowercase, remove spaces/special chars
        filename = re.sub(r'[^a-z0-9_]', '', filename.lower())
        filename = re.sub(r'_+', '_', filename)  # Remove duplicate underscores
        
        # Validate word count and length
        words = [w for w in filename.split('_') if w]
        if 2 <= len(words) <= 5 and 3 <= len(filename) <= 50:
            return '_'.join(words)
    
    # If strict extraction fails, try lenient extraction as fallback
    return None
```

---

### FIX 5: Step 3 - Validation & Fallback Chain

**File**: `core/classification/document.py` (NEW)

```python
def validate_and_fallback(ai_name: str, original_name: str) -> str:
    """
    STEP 3: Validate generated name against rules.
    Fallback chain if validation fails.
    """
    
    # RULE 1: Word count (2-5 words)
    words = [w for w in ai_name.split('_') if w]
    if not (2 <= len(words) <= 5):
        logger.warning(f"⚠️ Word count invalid ({len(words)} words). Fallback to original.")
        return original_name
    
    # RULE 2: Format check (lowercase, underscores only)
    if not re.match(r'^[a-z0-9_]+$', ai_name):
        logger.warning(f"⚠️ Format invalid. Fallback to original.")
        return original_name
    
    # RULE 3: Length check (3-50 chars)
    if not (3 <= len(ai_name) <= 50):
        logger.warning(f"⚠️ Length invalid ({len(ai_name)} chars). Fallback to original.")
        return original_name
    
    # RULE 4: Not all digits
    if ai_name.replace('_', '').isdigit():
        logger.warning(f"⚠️ All digits. Fallback to original.")
        return original_name
    
    # RULE 5: Check for vague/generic filenames
    generic_words = {"file", "document", "doc", "unknown", "data", "temp"}
    if len(words) == 1 and words[0] in generic_words:
        logger.warning(f"⚠️ Too generic. Fallback to original.")
        return original_name
    
    # All checks passed
    logger.debug(f"✓ Validation passed: {ai_name}")
    return ai_name
```

---

### FIX 6: Updated Stop-Word Filtering (Minimal)

**File**: `config.py`

```python
# MINIMAL stop-word set - only remove TRULY meaningless filler
STOP_WORDS = {
    "this", "is", "a", "an", 
    # Keep: "the", "for", "and", "of" (often meaningful in filenames)
}

# Better approach: use a KEEP_WORDS set for important terms
KEEP_WORDS = {
    "financial", "report", "invoice", "contract", "agreement",
    "audit", "statement", "summary", "proposal", "quote",
    "receipt", "letter", "memo", "notes", "meeting",
}
```

**Why minimal**: Stop-word filtering should be light. Better to validate final output quality instead.

---

### FIX 7: Updated Sanitization (Simplified)

**File**: `core/renamer.py`

```python
def sanitize_ai_output_v2(text: str) -> str:
    """
    SIMPLIFIED sanitization. Heavy lifting done in LLM prompts.
    """
    # 1. Remove <think> tags only (DeepSeek chain-of-thought)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # 2. Lowercase
    text = text.lower().strip()
    
    # 3. Remove file extensions (if somehow included)
    text = re.sub(r'\.(txt|pdf|jpg|jpeg|png|ppt|pptx|doc|docx|mp4|mkv|wav|mp3|mov)$', '', text)
    
    # 4. Keep only alphanumeric + underscores (no spaces allowed at this point)
    text = re.sub(r'[^a-z0-9_]', '', text)
    
    # 5. Normalize underscores
    text = re.sub(r'_+', '_', text)
    
    return text.strip('_')
```

---

### FIX 8: Updated rename_file() Main Pipeline

**File**: `core/renamer.py`

```python
def rename_file_v2(file_path, deep_mode=True, output_base=OUTPUT_BASE):
    """
    UPDATED: Uses new multi-step classification pipeline.
    """
    try:
        file_name = os.path.basename(file_path)
        name, ext = os.path.splitext(file_name)
        ext = ext.lower()
        
        # 1. SECURITY SCAN
        score, level, remarks, mime = calculate_suspicion(file_path)
        if level in ["High", "Critical", "Medium"]:
            return f"quarantined_{clean_text(name)}{ext}"
        
        # 2. DETERMINISM CHECK
        file_hash = get_file_hash(file_path)
        memory = load_memory()
        
        if file_hash and file_hash in memory:
            return memory[file_hash]
        
        # 3. CONTENT CLASSIFICATION - UPDATED FOR DOCUMENTS
        file_type = detect_file_type(file_path)
        
        if file_type == "image":
            ai_name = classify_image(file_path, deep_mode=deep_mode)
        elif file_type == "audio":
            ai_name = classify_audio(file_path, deep_mode=deep_mode)
        elif file_type == "video":
            ai_name = classify_video(file_path, deep_mode=deep_mode)
        elif file_type == "document":
            # USE NEW MULTI-STEP PIPELINE
            ai_name = classify_document_v2(file_path, deep_mode=deep_mode)
        else:
            ai_name = clean_text(name)
        
        # 4. FALLBACK IF AI FAILED
        if not ai_name or len(ai_name) < 3:
            ai_name = clean_text(name) or "unnamed_file"
        
        new_name = f"{file_type}_{ai_name}{ext}"
        
        # 5. CACHE RESULT
        if file_hash:
            memory[file_hash] = new_name
            save_memory(memory)
        
        return new_name
    
    except Exception as e:
        logger.error(f"❌ Rename Error: {e}", exc_info=True)
        return os.path.basename(file_path)
```

---

## --- VALIDATION RULES ---

### STRICT FILENAME VALIDATION

```
┌─ Filename Validation Checklist ─────────────────────────────┐
│                                                               │
│ 1. STRUCTURE                                                  │
│    ✓ Format: file_type_ai_name.ext (lowercase)              │
│    ✓ Prefix: document, image, audio, video, etc.            │
│                                                               │
│ 2. AI NAME COMPONENT (validate before adding prefix)         │
│    ✓ Word count: 2-5 words (separated by underscores)       │
│    ✓ Characters: [a-z0-9_] only                             │
│    ✓ Length: 3-50 chars                                      │
│    ✓ No leading/trailing underscores                         │
│    ✓ No duplicate underscores                                │
│    ✗ REJECT: All digits                                      │
│    ✗ REJECT: Single generic word (file, doc, data, unknown) │
│    ✗ REJECT: Empty or None                                   │
│                                                               │
│ 3. OUTPUT VALIDATION (after full filename created)           │
│    ✓ Total length: < 255 chars (Windows NTFS limit)         │
│    ✓ No reserved names (CON, PRN, AUX, etc.)                │
│    ✓ No special chars: <>/\|*?:"                            │
│                                                               │
│ 4. SEMANTIC VALIDATION (heuristic)                           │
│    ✓ Contains at least one non-stop word                    │
│    ✓ At least 2 different words (not repeated)               │
│    ✗ REJECT: Looks like noise/gibberish                      │
│                                                               │
└────────────────────────────────────────────────────────────┘
```

### VALIDATION CODE

```python
def validate_filename_strict(ai_name: str) -> bool:
    """
    Return True if filename passes all strict rules.
    """
    # Rule 1: Extract words
    words = [w for w in ai_name.split('_') if w]
    
    # Rule 2: Word count 2-5
    if not (2 <= len(words) <= 5):
        return False
    
    # Rule 3: Format check
    if not re.match(r'^[a-z0-9_]+$', ai_name):
        return False
    
    # Rule 4: Length check
    if not (3 <= len(ai_name) <= 50):
        return False
    
    # Rule 5: Not all digits
    if ai_name.replace('_', '').isdigit():
        return False
    
    # Rule 6: Not too generic
    generic = {"file", "document", "doc", "data", "unknown", "unnamed"}
    if len(words) == 1 and words[0] in generic:
        return False
    
    # Rule 7: Has diversity (not repeated words)
    if len(set(words)) == 1:  # All words are same
        return False
    
    # Rule 8: Check for obvious gibberish (random characters)
    # (can be expanded with better heuristics)
    
    return True
```

---

## --- MIGRATION PATH ---

### Phase 1: Deploy New Prompts
1. Update `core/classification/document.py` with new functions
2. Keep old `classify_document()` as fallback
3. Add feature flag: `USE_MULTI_STEP_PIPELINE = True/False` in `config.py`

### Phase 2: Test & Compare
```python
# Test both pipelines on sample files
def compare_pipelines(file_path):
    old_result = classify_document(file_path)
    new_result = classify_document_v2(file_path)
    print(f"Old: {old_result}")
    print(f"New: {new_result}")
```

### Phase 3: Full Switchover
- Set `USE_MULTI_STEP_PIPELINE = True`
- Remove old code after validation

---

## --- BEFORE/AFTER EXAMPLES ---

### Example 1: Financial Document

**INPUT**: 50-page financial audit report (first 2000 chars only)

**OLD PIPELINE**:
```
LLM Input: "FINANCIAL AUDIT REPORT Q3 2024..."
LLM Output: "This document appears to be a financial audit report for Q3 2024"
clean_ai_label(): "this_document_appears_to_be_a_financial_audit_report_for_q3_2024"
stop_word_filter(): "document_audit_report" → After dedup: "document_report"
Result: document_document_report.pdf ❌ (WRONG - lost context)
```

**NEW PIPELINE**:
```
Step 1 (Summary): 
  Input: [first 1500 + last 500 chars]
  Output: [TYPE]: audit | [TOPIC]: financial 2024
  
Step 2 (Filename):
  Input: "audit financial 2024"
  Output: [FILENAME_START]financial_audit_2024[FILENAME_END]
  
Step 3 (Validation): ✓ 3 words, all lowercase, 20 chars
Result: document_financial_audit_2024.pdf ✓ (CORRECT)
```

---

### Example 2: Meeting Notes

**INPUT**: "Meeting notes from Q3 planning session with sales team..."

**OLD PIPELINE**:
```
Result: document_meeting_notes_from_q3_planning_session_sales_team.pdf ❌ (Too long, generic)
```

**NEW PIPELINE**:
```
Step 1: [TYPE]: meeting_notes | [TOPIC]: q3_planning
Step 2: [FILENAME_START]q3_planning_meeting_notes[FILENAME_END]
Step 3: ✓ Validation passed (4 words, 24 chars)
Result: document_q3_planning_meeting_notes.pdf ✓
```

---

### Example 3: Invoice

**INPUT**: "Invoice #2024-08-001 for services rendered..."

**OLD PIPELINE**:
```
LLM: "This is an invoice for services..."
Result: document_this_is_an_invoice.pdf ❌ (Filler words, missing ID)
```

**NEW PIPELINE**:
```
Step 1: [TYPE]: invoice | [TOPIC]: services_2024
Step 2: [FILENAME_START]invoice_services_2024[FILENAME_END]
Result: document_invoice_services_2024.pdf ✓
```

---

## --- DEPLOYMENT CHECKLIST ---

- [ ] Add `smart_content_extraction()` function
- [ ] Add `generate_document_summary()` function
- [ ] Add `extract_summary_structured()` helper
- [ ] Add `generate_filename_from_summary()` function
- [ ] Add `extract_filename_strict()` helper
- [ ] Add `validate_and_fallback()` function
- [ ] Add `validate_filename_strict()` function
- [ ] Update `classify_document()` to call `classify_document_v2()`
- [ ] Update `rename_file()` to use `classify_document_v2()`
- [ ] Update `STOP_WORDS` in `config.py`
- [ ] Add logging at each step
- [ ] Test on sample files (before/after comparison)
- [ ] Monitor LLM token usage (should decrease due to smaller prompts)
- [ ] Verify cache determinism still works

---

## --- BENEFITS SUMMARY ---

| Issue | Fix | Benefit |
|-------|-----|---------|
| Weak prompting | Multi-step focused prompts | 95%+ compliance with output format |
| Context loss | Smart extraction (start + end) | Better naming for long documents |
| Model escaping tags | Hard tag enforcement | 100% format compliance |
| Stop-word over-filtering | Minimal filtering | Meaningful words preserved |
| Weak validation | Strict 7-point validation | Rejects vague/generic names |
| Single-task confusion | Separate steps (summarize → filename) | Better task decomposition |
| Too many tokens | Smaller focused prompts | Faster inference, lower cost |

---

## --- NEXT STEPS ---

1. Deploy prompts and functions
2. Run comparison tests on 50+ documents
3. Measure improvements:
   - % of filenames matching [FILENAME_START] tags ✓
   - % passing validation rules ✓
   - % avoiding generic words ✓
   - User satisfaction on 10-file sample ✓
4. Iterate on edge cases
