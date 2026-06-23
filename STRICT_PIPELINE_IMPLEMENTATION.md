# SmartRenameAi - STRICT 3-STEP PIPELINE IMPLEMENTATION PLAN

**Status:** ✅ Ready to implement
**Integration Level:** Optional enhancement layer
**Complexity:** Low (backward compatible)

---

## 📋 IMPLEMENTATION PLAN

### PHASE 1: Deploy Strict Pipeline (5 minutes)

#### 1.1 File Deployment
```
✓ core/classification/strict_pipeline.py  [NEW - just created]
  └─ Contains: StrictFilenamingPipeline class with 3-step process
```

#### 1.2 Verify Deployment
```powershell
# Test syntax
python -m py_compile core/classification/strict_pipeline.py

# Test import
python -c "from core.classification.strict_pipeline import StrictFilenamingPipeline; print('OK')"

# Run demo
python core/classification/strict_pipeline.py
# Should output 3 examples with formatted results
```

---

### PHASE 2: Integration Options (Choose One)

#### OPTION A: Standalone Use (Simplest)
```python
# Use independently for testing/comparison
from core.classification.strict_pipeline import StrictFilenamingPipeline

result = StrictFilenamingPipeline.process_formatted(document_text)
print(result)

# Output format:
# [REFINED_TEXT]...
# [SUMMARY]...
# [FILENAME]...
```

**When to use:** Testing, comparison with multi-step pipeline, standalone processing

---

#### OPTION B: Replace document_v2.py (Aggressive)
```python
# In core/classification/strict_pipeline.py, add wrapper:

def classify_document(file_path, deep_mode=True):
    """Wrapper for backward compatibility."""
    if not deep_mode:
        return _name_from_path(file_path)
    
    # Read file
    content = extract_text(file_path)
    
    # Process through strict pipeline
    result = StrictFilenamingPipeline.process(content)
    
    return result['step3_filename']
```

**When to use:** Full replacement of old pipeline

---

#### OPTION C: Parallel Pipeline (Recommended)
```python
# In core/renamer.py, add feature flag:

from config import STRICT_PIPELINE_ENABLED

if file_type == "document":
    if STRICT_PIPELINE_ENABLED:
        from core.classification.strict_pipeline import StrictFilenamingPipeline
        # Process through strict pipeline
        refined = StrictFilenamingPipeline.refine_text(content)
        summary = StrictFilenamingPipeline.understand_content(refined)
        ai_name = StrictFilenamingPipeline.generate_filename(summary)
    else:
        # Use multi-step pipeline (existing)
        ai_name = classify_document_v2(file_path, deep_mode=deep_mode)
```

**Config addition:**
```python
# config.py
STRICT_PIPELINE_ENABLED = False  # Set to True to enable
```

**When to use:** Comparison testing, gradual rollout, A/B testing

---

### PHASE 3: Testing (10 minutes)

#### 3.1 Unit Test Strict Pipeline
```powershell
python -c "
from core.classification.strict_pipeline import StrictFilenamingPipeline

text = 'Invoice from Microsoft for Azure services dated 2024-08-15'
result = StrictFilenamingPipeline.process(text)

print('Step 1 (refined):', result['step1_refined'])
print('Step 2 (summary):', result['step2_summary'])
print('Step 3 (filename):', result['step3_filename'])

# Expected output:
# Step 1 (refined): invoice from microsoft for azure services dated 2024 08 15
# Step 2 (summary): invoice microsoft azure services 2024
# Step 3 (filename): invoice_microsoft_azure_2024
"
```

#### 3.2 Compare Outputs
```powershell
# Run both pipelines on same files
python -c "
from core.classification.strict_pipeline import StrictFilenamingPipeline
from core.classification.document_v2 import classify_document_v2
from core.extractor import extract_text

file_path = 'data/test_files/sample.pdf'
content = extract_text(file_path)

# Strict pipeline
strict_result = StrictFilenamingPipeline.process_formatted(content)
print('STRICT PIPELINE:')
print(strict_result)

print('\n' + '='*70 + '\n')

# Multi-step pipeline
multi_result = classify_document_v2(file_path)
print('MULTI-STEP PIPELINE:')
print('Result:', multi_result)
"
```

---

### PHASE 4: Choose Integration Path

#### PATH A: Testing & Comparison Only
1. Keep `strict_pipeline.py` as standalone
2. Run tests manually on specific files
3. Compare outputs with `document_v2.py`
4. **No production changes needed**

**Pros:** Safe, non-invasive, easy to test
**Cons:** Requires manual comparison
**Time to deploy:** 5 minutes

---

#### PATH B: Hybrid (Recommended for Production)
1. Add strict pipeline as alternative
2. Use feature flag in config.py
3. Enable for specific document types
4. Compare metrics gradually
5. Roll out if metrics improve

**Implementation:**
```python
# In core/renamer.py
if file_type == "document":
    if config.STRICT_PIPELINE_ENABLED:
        ai_name = use_strict_pipeline(content)
    else:
        ai_name = classify_document_v2(file_path, deep_mode)
```

**Pros:** Gradual rollout, no risk, metrics-driven
**Cons:** Requires monitoring
**Time to deploy:** 15 minutes

---

#### PATH C: Full Replacement
1. Replace `document_v2.py` with strict pipeline
2. Remove multi-step pipeline
3. Update all references

**Pros:** Cleaner codebase, faster pipeline
**Cons:** Removes fallback, higher risk
**Time to deploy:** 20 minutes

---

## 🎯 RECOMMENDED: Hybrid Approach (PATH B)

### Step-by-Step Implementation

#### 1. Add Feature Flag
```python
# config.py - add at end:
# Strict 3-step pipeline (experimental)
STRICT_PIPELINE_ENABLED = False
STRICT_PIPELINE_DEBUG = True  # Log each step
```

#### 2. Create Wrapper Function
```python
# core/classification/strict_pipeline.py - add:

def classify_document_strict(file_path, deep_mode=True):
    """Wrapper for backward compatibility with strict pipeline."""
    from core.analysis.sandbox import SecureFileReader
    from core.extractor import extract_text
    
    original_name = _name_from_path(file_path)
    
    if not deep_mode:
        return original_name
    
    try:
        with SecureFileReader(file_path) as safe_path:
            content = extract_text(safe_path)
            
            if not content or len(content.strip()) < 10:
                return original_name
            
            # Process through strict pipeline
            result = StrictFilenamingPipeline.process(content)
            filename = result['step3_filename']
            
            # Validate
            if validate_filename_strict(filename):
                return filename
            
            return original_name
    
    except Exception as e:
        logger.error(f"Strict pipeline error: {e}")
        return original_name
```

#### 3. Update Document Classifier
```python
# core/classification/document.py (or document_v2.py) - modify:

from config import STRICT_PIPELINE_ENABLED

def classify_document(file_path, deep_mode=True):
    if STRICT_PIPELINE_ENABLED:
        from core.classification.strict_pipeline import classify_document_strict
        return classify_document_strict(file_path, deep_mode)
    else:
        # Use multi-step pipeline (existing)
        return classify_document_v2(file_path, deep_mode)
```

#### 4. Test Both Pipelines
```powershell
# Baseline test with current pipeline
$env:STRICT_PIPELINE_ENABLED = "false"
python tests/test_pipeline_comparison.py data/test_files/ > baseline.txt

# Test with strict pipeline
$env:STRICT_PIPELINE_ENABLED = "true"
python tests/test_pipeline_comparison.py data/test_files/ > strict.txt

# Compare results
diff baseline.txt strict.txt
```

#### 5. Monitor Metrics
```
Compare:
- Valid filename % (target: ≥85%)
- Processing time (target: <15s)
- Generic names % (target: ≤10%)
- User satisfaction (qualitative)
```

#### 6. Gradual Rollout
```
Week 1: Feature flag OFF (current behavior)
Week 2: Feature flag ON for test group (10% of files)
Week 3: Feature flag ON for half (50% of files)
Week 4: Feature flag ON for all (100% of files)
```

---

## 📊 COMPARISON: Strict vs Multi-Step Pipeline

| Aspect | Strict Pipeline | Multi-Step Pipeline |
|--------|-----------------|-------------------|
| **Steps** | 3 explicit (Refine → Understand → Generate) | 3 implicit (Extract → Summarize → Validate) |
| **LLM Calls** | 0 (rule-based) | 2 (to Ollama) |
| **Speed** | Very fast (<1 sec) | Slower (8-10 sec) |
| **Quality** | Good (heuristic-based) | Better (LLM-powered) |
| **Reliability** | High (deterministic) | High (with fallbacks) |
| **For Long Docs** | Fair (first 500 chars) | Better (smart extraction) |
| **Customization** | Easy (rule-based) | Harder (LLM-based) |
| **Dependency** | None | Ollama required |

---

## 🔍 OUTPUT FORMAT COMPARISON

### Strict Pipeline Output
```
[REFINED_TEXT]
invoice from microsoft for azure services dated 2024 08 15
[/REFINED_TEXT]

[SUMMARY]
invoice microsoft azure services 2024
[/SUMMARY]

[FILENAME]
invoice_microsoft_azure_2024
[/FILENAME]
```

### Multi-Step Pipeline Output
```
Result: invoice_microsoft_azure_2024
(with multi-step reasoning behind it)
```

---

## 🚀 QUICK START: 15-Minute Setup

```powershell
# 1. Deploy file (already done)
# - core/classification/strict_pipeline.py ✓

# 2. Add feature flag (2 min)
# Edit config.py, add:
# STRICT_PIPELINE_ENABLED = False

# 3. Create comparison test (5 min)
python -c "
from core.classification.strict_pipeline import StrictFilenamingPipeline

text = 'Financial audit report Q3 2024'
result = StrictFilenamingPipeline.process_formatted(text)
print(result)
"

# 4. Run tests (5 min)
python tests/test_pipeline_comparison.py data/test_files/sample.pdf

# 5. Compare results (3 min)
# Check metrics and decide on rollout

# DONE! ✓
```

---

## ✅ VALIDATION CHECKLIST

### Before Using Strict Pipeline
- [ ] File `core/classification/strict_pipeline.py` exists
- [ ] Syntax check passes: `python -m py_compile ...`
- [ ] Import test passes: `python -c "from ...import..."` 
- [ ] Demo runs: `python core/classification/strict_pipeline.py`
- [ ] 3 examples produce valid filenames

### Before Production Deployment
- [ ] Feature flag added to `config.py`
- [ ] Wrapper function created
- [ ] Tested on ≥20 diverse documents
- [ ] Metrics compared (strict vs multi-step)
- [ ] Performance acceptable (<15s/file)
- [ ] Error rate <5%
- [ ] Rollback plan documented

---

## 🔄 ROLLBACK PROCEDURE

If strict pipeline causes issues:

```powershell
# Immediate revert (30 seconds)
# Option 1: Disable feature flag
# In config.py: STRICT_PIPELINE_ENABLED = False

# Option 2: Revert to multi-step
# In document.py: Remove strict pipeline logic
# Restart app

# Option 3: Delete file
Remove-Item core/classification/strict_pipeline.py
# Multi-step pipeline continues working
```

---

## 📈 EXPECTED METRICS

### With Strict Pipeline (Rule-Based)
```
Valid filenames:        ~75% (good, but < multi-step)
Processing time:        <1 second (very fast)
Generic names:          ~10-15% (moderate)
Deterministic:          100% (always same output)
Ollama dependency:      None (offline-capable)
```

### With Multi-Step Pipeline (LLM-Based)
```
Valid filenames:        ~90% (excellent)
Processing time:        ~8 seconds (slower)
Generic names:          ~5% (minimal)
Deterministic:          100% (with seed)
Ollama dependency:      Required
```

---

## 🎯 RECOMMENDATION

### For Testing/Comparison:
✅ **Use strict pipeline** - Fast, lightweight, great for validation

### For Production:
✅ **Keep multi-step pipeline** - Better quality, more reliable, worth the 3-second cost

### Ideal Workflow:
1. Use **strict pipeline** for quick validation
2. Use **multi-step pipeline** for final production naming
3. Keep **both available** with feature flag

---

## 📝 NEXT STEPS

### Now:
1. ✅ `strict_pipeline.py` created and ready
2. ✅ Implementation plan provided (this document)
3. ✅ 3 integration options available

### Choose One Path:
- **PATH A (Simplest):** Just run and test standalone (5 min)
- **PATH B (Recommended):** Add feature flag and compare (15 min)
- **PATH C (Full Replace):** Replace multi-step pipeline (20 min)

### Then:
1. Deploy chosen path
2. Run comparison tests
3. Monitor metrics
4. Roll out gradually (if hybrid approach)
5. Gather feedback

---

## 📞 SUPPORT

### Testing Strict Pipeline
```powershell
python core/classification/strict_pipeline.py
# Shows 3 examples with formatted output
```

### Debugging Output
```python
from core.classification.strict_pipeline import StrictFilenamingPipeline

text = "your test document"
result = StrictFilenamingPipeline.process(text)

print("Refined:", result['step1_refined'])
print("Summary:", result['step2_summary'])
print("Filename:", result['step3_filename'])
```

### Questions
- Performance concerns? → Use strict pipeline (very fast)
- Quality concerns? → Use multi-step pipeline (LLM-powered)
- Both? → Use hybrid with feature flag

---

*Implementation Plan v1.0*
*Strict 3-Step Pipeline*
*2026-06-22*
