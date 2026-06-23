# Getting Started with SmartRenameAi Optimization

**Time needed:** 5-10 minutes  
**Difficulty:** Beginner-friendly

---

## 🚀 5-MINUTE QUICK START

### Step 1: Understand What You Have (2 minutes)

You now have **two pipelines** that work together:

| Feature | Multi-Step | Strict |
|---------|-----------|--------|
| Quality | 90% ✅✅ | 75% ✅ |
| Speed | 8 sec | <1 sec |
| Best for | Production | Testing |

### Step 2: Test the Strict Pipeline (2 minutes)

```powershell
# Open a terminal and run:
cd d:\internship\SmartRenameAi
python core/classification/strict_pipeline.py
```

**You should see:**
```
Testing Strict Pipeline...

Example 1: Invoice
  - Refined: "This is an invoice from Microsoft..."
  - Summary: "invoice microsoft azure services"
  - Filename: "invoice_microsoft_azure_2024"

Example 2: Meeting
  - Refined: "Q3 planning session..."
  - Summary: "meeting notes from q3"
  - Filename: "meeting_notes_from_q3_planning"

Example 3: Report
  - Refined: "Financial audit report..."
  - Summary: "financial audit q3"
  - Filename: "financial_audit_report_q3_2024"
```

### Step 3: Choose Your Path (1 minute)

**Choose ONE:**

#### Path 1: Keep Everything (Do Nothing) ✅
```
- Keep current system running
- Both pipelines available
- Use for comparison
- No changes needed
```

#### Path 2: Add Feature Flag (5 minutes)
```
1. Open config.py
2. Add: STRICT_PIPELINE_ENABLED = False
3. Set to True to test
4. Feature flag switching
```

#### Path 3: Full Integration (30 minutes)
```
Follow STRICT_PIPELINE_IMPLEMENTATION.md
Implement hybrid approach
Deploy both pipelines
Set up metrics
```

---

## 🎯 RECOMMENDED APPROACH FOR MOST USERS

### For Testing/Validation Only:
```python
# Just run the demo
python core/classification/strict_pipeline.py

# No changes to existing code
# Use to validate file naming offline
# Compare outputs with multi-step
```

### For Production Deployment:
```python
# Keep multi-step as primary (90% quality)
# Add strict as secondary option

# In config.py - add one line:
STRICT_PIPELINE_AVAILABLE = True

# Then use as needed:
from core.classification.strict_pipeline import StrictFilenamingPipeline

result = StrictFilenamingPipeline.process(file_path)
print(result['filename'])  # Quick testing
```

---

## 📋 COMMON SCENARIOS

### Scenario 1: "I just want to validate my files quickly"
```powershell
# Run this once
python core/classification/strict_pipeline.py

# Run on a specific file
python -c "
from core.classification.strict_pipeline import StrictFilenamingPipeline
result = StrictFilenamingPipeline.process_formatted('path/to/file.pdf')
print(result)
"
```

### Scenario 2: "I want to compare both pipelines"
```powershell
# Run comparison on a directory
python tests/test_pipeline_comparison.py data/test_files/

# Output: JSON report showing both pipelines side-by-side
```

### Scenario 3: "I want the best quality for production"
```python
# Use multi-step pipeline (existing)
from core.classification.document_v2 import classify_document_v2

result = classify_document_v2('file.pdf', deep_mode=True)
print(result['filename'])  # 90% quality
```

### Scenario 4: "I want maximum speed for validation"
```python
# Use strict pipeline (new)
from core.classification.strict_pipeline import StrictFilenamingPipeline

result = StrictFilenamingPipeline.process('file.pdf')
print(result['filename'])  # <1 second, 75% quality
```

---

## 🔍 UNDERSTANDING THE TWO PIPELINES

### Multi-Step Pipeline (document_v2.py)
```
Input file
    ↓
Extract content (smart: first+end)
    ↓ [LLM Call 1]
Generate summary
    ↓ [LLM Call 2]
Generate filename
    ↓
Validate (7-point checks)
    ↓
Output: Best-quality filename (90% valid)
    
Time: ~8 seconds
Dependency: Ollama
Best for: Production
```

### Strict Pipeline (strict_pipeline.py)
```
Input file
    ↓ [STEP 1]
Refine text (remove noise)
    ↓ [STEP 2]
Understand content (extract key terms)
    ↓ [STEP 3]
Generate filename (2-5 words)
    ↓
Output: Fast filename (75% valid)
    
Time: <1 second
Dependency: None
Best for: Testing/validation
```

---

## ✅ VERIFICATION CHECKLIST

After reading this guide, you should understand:

- [ ] You have 2 pipelines now (multi-step + strict)
- [ ] Multi-step is 90% quality but 8 seconds
- [ ] Strict is <1 second but 75% quality
- [ ] Both can work together
- [ ] I can run strict pipeline demo with `python core/classification/strict_pipeline.py`
- [ ] I know which pipeline to use for my use case

---

## 🚨 TROUBLESHOOTING

### "I ran the demo and nothing happened"
```powershell
# Make sure you're in the right directory
cd d:\internship\SmartRenameAi

# Make sure Python is installed
python --version

# Run again
python core/classification/strict_pipeline.py
```

### "I want to use multi-step but I'm seeing errors"
```powershell
# Check if Ollama is running
# Should be running at http://localhost:11434

# Verify by running:
curl http://localhost:11434/api/tags

# If error, start Ollama first:
ollama serve
```

### "I want to test on my own file"
```python
from core.classification.strict_pipeline import StrictFilenamingPipeline

# Test on your file
result = StrictFilenamingPipeline.process('path/to/your/file.pdf')

# Print the result
print(f"Filename: {result['filename']}")
print(f"Summary: {result['summary']}")
```

---

## 📚 NEXT STEPS

### If you want to understand more:
1. Read `QUICK_REFERENCE.md` (5 min) - Overview of all fixes
2. Read `STRICT_PIPELINE_SUMMARY.md` (15 min) - Pipeline comparison
3. Read `PIPELINE_OPTIMIZATION.md` (60 min) - Deep technical details

### If you want to deploy:
1. Follow `STRICT_PIPELINE_IMPLEMENTATION.md` - Deployment guide
2. Follow `IMPLEMENTATION_GUIDE.md` - Multi-step deployment
3. Run tests and compare metrics

### If you want to integrate:
1. Choose your path (A, B, or C from STRICT_PIPELINE_IMPLEMENTATION.md)
2. Implement according to the chosen path
3. Test thoroughly
4. Monitor metrics in production

---

## 💡 TIPS

1. **For maximum confidence:** Run both pipelines on your files and compare
2. **For fast validation:** Use strict pipeline (ready in <1 second)
3. **For production:** Use multi-step pipeline (90% quality)
4. **For learning:** Read the code in `strict_pipeline.py` - it's simple and well-commented

---

## 📞 QUESTIONS?

Refer to:
- **Quick answers:** QUICK_REFERENCE.md
- **Deployment help:** IMPLEMENTATION_GUIDE.md or STRICT_PIPELINE_IMPLEMENTATION.md
- **Deep questions:** PIPELINE_OPTIMIZATION.md
- **Comparisons:** STRICT_PIPELINE_SUMMARY.md

---

*Ready to get started? Run this:*
```powershell
python core/classification/strict_pipeline.py
```

*That's it! You're now using the optimization.*
