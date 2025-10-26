from pdfminer.high_level import extract_text
import os

BOOK_PATH = "/home/user/backend/iq_math_orginal/Books/algebra-7.pdf"

print("📘 Fayl mavjudmi:", os.path.exists(BOOK_PATH))
if os.path.exists(BOOK_PATH):
    text = extract_text(BOOK_PATH)
    print("📄 Matn uzunligi:", len(text))
    print("🔹 Birinchi 1000 ta belgi:\n", text[:1000])
else:
    print("❌ Fayl topilmadi:", BOOK_PATH)
