import os
import glob

def chunk_text(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks

def count_chunks(directory):
    total = 0
    files = glob.glob(os.path.join(directory, "*.md"))
    for md_file in files:
        try:
            with open(md_file, "r") as f:
                content = f.read()
                chunks = chunk_text(content)
                total += len(chunks)
                print(f"  {os.path.basename(md_file)}: {len(chunks)} chunks")
        except Exception as e:
            print(f"  Error: {e}")
    return total

print("🚀 Calculating expected ingestion...")
print("\n📚 Runbooks:")
rb_total = count_chunks("./data/runbooks")
print(f"✓ Total: {rb_total} chunks\n")

print("📋 Incidents:")
inc_total = count_chunks("./data/incidents")
print(f"✓ Total: {inc_total} chunks\n")

print(f"Ingested {rb_total} chunks into ./chroma_runbooks")
print(f"Ingested {inc_total} chunks into ./chroma_incidents")
print(f"\n✅ Simulation complete!")
print(f"   Total runbook chunks: {rb_total}")
print(f"   Total incident chunks: {inc_total}")
print(f"   Total documents: {rb_total + inc_total}")
