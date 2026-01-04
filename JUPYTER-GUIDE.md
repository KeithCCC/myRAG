# How to Use Jupyter Notebook

## ✅ Jupyter Notebook Installed Successfully!

---

## Quick Start

### 1. **Open the Demo Notebook in VS Code**

The notebook is already open: `demo_notebook.ipynb`

### 2. **Run Cells**

**Option A: Run all cells at once**
- Click the "Run All" button at the top of the notebook
- Or press `Ctrl+Shift+Enter`

**Option B: Run cells one by one**
- Click the ▶️ play button next to each cell
- Or press `Shift+Enter` to run current cell and move to next

### 3. **View Results**

Each cell will show output below it:
- ✓ Text output
- ✓ Tables and data
- ✓ Search results

---

## What the Demo Shows

### Cell 1-2: **Setup**
- Imports all modules
- Verifies installation

### Cell 3-4: **Japanese Tokenizer**
- Shows MeCab splitting Japanese text
- Compares with English text

### Cell 5-6: **Database**
- Creates test documents
- Adds Japanese and English chunks

### Cell 7-9: **Search**
- Tests Japanese keyword search ("機械学習", "深層")
- Tests English keyword search ("programming", "Python")
- Shows ranked results with scores

### Cell 10-11: **Configuration**
- Displays current settings
- Shows statistics

---

## Alternative: Use Jupyter in Browser

If you prefer the classic Jupyter interface:

```powershell
# In terminal:
jupyter notebook
```

This will:
1. Start Jupyter server
2. Open browser automatically
3. Navigate to `demo_notebook.ipynb`
4. Click cells and run them

To stop: Press `Ctrl+C` in terminal

---

## Tips

**Edit cells:**
- Double-click any cell to edit
- Try changing search queries
- Add your own test data

**Restart kernel:**
- Click "Restart" button at top
- Use if something goes wrong

**Add new cells:**
- Click `+` button
- Choose "Code" or "Markdown"

---

## What You Can Try

### Modify Search Queries:
```python
# Try these in a new cell:
search_and_display("ニューラル")  # Japanese
search_and_display("learning")    # English
search_and_display("データ")      # Japanese
```

### Add Your Own Chunks:
```python
# Add a new chunk in Japanese:
new_chunk = Chunk(
    id=str(uuid.uuid4()),
    document_id=doc1.id,
    page=5,
    start_offset=500,
    end_offset=600,
    text="あなたのテキストをここに入力",
    text_hash="custom_hash"
)
db.add_chunk(new_chunk)

# Search for it:
search_and_display("あなた")
```

### Change Settings:
```python
# Try different chunk sizes:
settings.chunk_size = 1000
config.save_settings(settings)
print(f"New chunk size: {settings.chunk_size}")
```

---

## Troubleshooting

**Cell won't run:**
- Check if kernel is running (top right corner)
- Click "Restart" kernel

**Import errors:**
- Make sure you're in myRAG folder
- Check virtual environment is activated

**No MeCab output:**
- MeCab should be installed
- Run first cell to verify

---

## Next Steps

Once you're comfortable with the notebook:
1. ✅ You understand the database structure
2. ✅ You can search Japanese and English text
3. ✅ You know how tokenization works

**Ready for Phase 2:** File indexing and PDF processing! 🚀

---

## Files Created

- `demo_notebook.ipynb` - Interactive demo notebook
- `requirements.txt` - Updated with Jupyter
- Virtual environment - Has all packages

**All ready to explore!** 📓
