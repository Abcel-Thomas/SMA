# SmartRenameAi - IMPLEMENTATION GUIDE

## Quick Start: Migrate to Fixed Pipeline

---

## STEP 1: Deploy New Code

### Option A: Replace Existing Code (Full Switchover)

**Backup first:**
```powershell
Copy-Item core/classification/document.py core/classification/document_backup.py
```

**Then replace content of `core/classification/document.py` with `core/classification/document_v2.py`:**
- Copy all code from `core/classification/document_v2.py`
- Paste into `core/classification/document.py`
- Delete `document_v2.py`

### Option B: Parallel Testing (Safe)

**Keep both files and test in parallel:**

1. Keep `core/classification/document.py` (old)
2. Keep `core/classification/document_v2.py` (new)
3. Update `core/renamer.py` to support both with feature flag

```python
# In core/renamer.py
from config import USE_NEW_PIPELINE

if file_type == "document":
    if USE_NEW_PIPELINE:
        from core.classification.document_v2 import classify_document_v2
        ai_name = classify_document_v2(file_path, deep_mode=deep_mode)
    else:
        from core.classification.document import classify_document
        ai_name = classify_document(file_path, deep_mode=deep_mode)
```

4. Add to `config.py`:
```python
# Feature flag - set to True to enable new multi-step pipeline
USE_NEW_PIPELINE = True
```

---

## STEP 2: Update Dependencies (if needed)

Check you have all required imports:
```powershell
pip list | grep -E "requests|loguru"
```

If missing:
```powershell
pip install requests
```

---

## STEP 3: Run Tests

### Test Single File
```powershell
cd d:\internship\SmartRenameAi
python tests/test_pipeline_comparison.py data/test_files/sample_document.pdf
```

### Test Batch (all PDFs in directory)
```powershell
python tests/test_pipeline_comparison.py data/test_files/
```

### Test via GUI
```powershell
python main.py
# Use GUI to select file and check preview before rename
```

---

## STEP 4: Monitor Results

### Check Logs
```powershell
tail -f logs/log.txt
```

Look for:
```
✓ Summary generated: invoice microsoft 2024
✓ Filename generated: invoice_microsoft_2024
✓ Filename validated: invoice_microsoft_2024
→ Step 1: Generating summary...
→ Step 2: Generating filename from summary...
→ Step 3: Validating...
```

### Check Cache (Determinism)
```powershell
cat data/processed_memory.json | jq .
```

Should see entries like:
```json
{
  "a1b2c3d4e5f6...": "document_invoice_2024.pdf",
  "f6e5d4c3b2a1...": "document_report_financial.pdf"
}
```

---

## VALIDATION CHECKLIST

Before deploying to production:

### Code Quality
- [ ] `document_v2.py` has no syntax errors
  ```powershell
  python -m py_compile core/classification/document_v2.py
  ```

- [ ] All imports work
  ```powershell
  python -c "from core.classification.document_v2 import classify_document_v2; print('OK')"
  ```

- [ ] No duplicate function definitions
  ```powershell
  grep -n "^def " core/classification/document_v2.py | wc -l
  ```

### Functional Testing

- [ ] Compare test with ≥10 files
  ```powershell
  python tests/test_pipeline_comparison.py data/test_files/
  ```

- [ ] Check metrics:
  - New pipeline valid %: Target ≥85%
  - Old pipeline valid %: Current baseline
  - Improvement: New - Old = positive value

### Integration

- [ ] Test with existing `renamer.py`
  ```python
  from core.renamer import rename_file
  result = rename_file("test.pdf", deep_mode=True)
  print(result)
  ```

- [ ] Test with GUI
  ```powershell
  python gui.py
  ```

- [ ] Test cache determinism
  ```python
  # Same file processed twice should return same result
  result1 = rename_file("test.pdf")
  result2 = rename_file("test.pdf")
  assert result1 == result2
  ```

---

## TROUBLESHOOTING

### Issue: LLM Returns Same Output Despite New Prompts

**Cause:** Old prompts still in cache or old code still running

**Fix:**
```powershell
# 1. Clear cache
Remove-Item data/processed_memory.json
# OR selectively delete entries:
python -c "
import json
memory = json.load(open('data/processed_memory.json'))
# Remove entries older than today
memory_filtered = {k: v for k, v in memory.items() if 'today' in str(v)}
json.dump(memory_filtered, open('data/processed_memory.json', 'w'))
"

# 2. Verify new code is running
grep -n "Step 1: Generating summary" core/classification/document_v2.py

# 3. Check logs
tail -f logs/log.txt | grep "Step 1"
```

### Issue: Ollama Connection Error

**Check Ollama is running:**
```powershell
curl http://localhost:11434/api/tags
```

**Start Ollama if needed:**
```powershell
# On Windows - usually runs as service
Start-Service Ollama

# Or manually:
& "C:\Program Files\Ollama\ollama.exe"

# Wait for startup (may take 10-30 seconds)
Start-Sleep -Seconds 5
```

### Issue: Timeout or Slow Performance

**New pipeline makes fewer LLM calls (better):**
- Old: 1 call (generate name directly)
- New: 2 calls (summarize → generate name)

**Performance expected:**
- Old pipeline: ~5 seconds/file
- New pipeline: ~8-10 seconds/file (trade-off for better quality)

**Optimize if needed:**
```python
# In document_v2.py, increase temperature slightly for faster inference
"temperature": 0.1,  # was 0.0 (slightly more random = faster)
```

### Issue: New Filenames Are Longer Than Old

**Normal behavior** - multi-step pipeline generates more descriptive names.

Example:
- Old: `document_invoice.pdf`
- New: `document_invoice_microsoft_2024.pdf`

**If too long, adjust in Step 2 prompt:**
```python
# Change from 2-5 words to:
# "Output EXACTLY 2-3 words" (instead of 2-5)
```

---

## ROLLBACK PLAN

If you need to revert to old pipeline:

### Option 1: Restore from Backup
```powershell
Copy-Item core/classification/document_backup.py core/classification/document.py
```

### Option 2: Switch Feature Flag
```python
# In config.py
USE_NEW_PIPELINE = False  # Revert to old
```

### Option 3: Delete New File
```powershell
Remove-Item core/classification/document_v2.py
# Old code will still run via document.py
```

---

## MONITORING & METRICS

### Track Quality Improvements

**Automated test every 100 files:**
```python
# Add to main.py
if file_count % 100 == 0:
    os.system("python tests/test_pipeline_comparison.py data/test_files/")
```

**Monthly comparison report:**
```powershell
# Generate report with 50 random test files
python tests/test_pipeline_comparison.py data/test_files/ > pipeline_report_$(Get-Date -Format yyyyMMdd).txt
```

### Key Metrics to Track

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| Valid filenames % | ≥90% | ? | % passing all validation rules |
| Format compliance % | 100% | ? | % with [FILENAME_START/END] tags extracted |
| Tag format success % | ≥95% | ? | % where tags found and parsed correctly |
| Avg filename length | 20-30 chars | ? | Too short = generic, too long = unwieldy |
| LLM timeout rate | <2% | ? | % requests timing out |
| Cache hit rate | ≥30% | ? | % files already in cache (determinism) |

---

## ADVANCED: Custom Tuning

### Adjust Prompt Aggressiveness

**Current**: Very strict (minimize false positives)

**If too many rejections**, soften validation:
```python
# In validate_filename_strict() - lower thresholds
if not (2 <= len(words) <= 6):  # was 2-5, now 2-6
    return False, "..."
```

### Adjust Token Budgets

**Current**: Summarize (100 tokens) + Filename (50 tokens) = 150 total

**For faster inference:**
```python
"num_predict": 75,   # was 100 - summarize faster
"num_predict": 30,   # was 50 - filename faster
```

**For better quality:**
```python
"num_predict": 150,  # was 100 - more thinking
"num_predict": 80,   # was 50 - more safety checks
```

### Add Custom Stop-Word List

```python
# In config.py - expand only if needed
STOP_WORDS = {
    "this", "is", "a", "an",
    # Add domain-specific stops here
    # "internal", "draft", "version",
}
```

---

## PRODUCTION CHECKLIST

Before full deployment:

- [ ] Tested on ≥50 diverse documents
- [ ] Validated with ≥3 team members
- [ ] Logging enabled and monitored
- [ ] Backup of original code made
- [ ] Rollback plan documented
- [ ] Cache cleared before go-live
- [ ] Monitored for first 24 hours
- [ ] Metrics baseline established
- [ ] Performance acceptable (<15s per file)
- [ ] Error rate <5%

---

## SUPPORT

### Getting Help

1. **Check logs first:**
   ```powershell
   tail -f logs/log.txt | grep -i error
   ```

2. **Enable debug logging:**
   ```python
   # In logs/logger.py
   logger.setLevel(DEBUG)  # was INFO
   ```

3. **Run comparison test:**
   ```powershell
   python tests/test_pipeline_comparison.py <problem_file>
   ```

### Reporting Issues

Include in bug report:
- Sample file (if possible)
- Log output (logs/log.txt)
- Expected vs actual filename
- Python version (`python --version`)
- Ollama model version (`ollama list`)
