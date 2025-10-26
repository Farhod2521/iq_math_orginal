from pdfminer.high_level import extract_text
import os, re

BOOK_PATH = "/home/user/backend/iq_math_orginal/Books/algebra-7.pdf"

# 1️⃣ PDF o‘qish
if not os.path.exists(BOOK_PATH):
    print("❌ Fayl topilmadi:", BOOK_PATH)
    exit()

text = extract_text(BOOK_PATH)
print(f"✅ PDF matn uzunligi: {len(text)}")

# 2️⃣ Normalizatsiya (qator va bo‘sh joylarni tozalaymiz)
def normalize(txt):
    return re.sub(r"\s+", " ", txt).strip().lower()

normalized_text = normalize(text)

# 3️⃣ Mavzu nomi
topic_name = "sonli ifodalar"

# 4️⃣ Mavzuni topamiz
pattern = re.compile(rf"{topic_name}", re.IGNORECASE)
match = pattern.search(normalized_text)
if not match:
    print(f"❌ Mavzu topilmadi: {topic_name}")
    exit()

start_index = match.start()
rest_text = normalized_text[start_index:]

# 5️⃣ Mashqlar bo‘limini topamiz
mashq_match = re.search(r"mashqlar", rest_text, re.IGNORECASE)
if not mashq_match:
    print("❌ Mashqlar bo‘limi topilmadi.")
    exit()

mashq_text = rest_text[mashq_match.end():]

# 6️⃣ Mashqlarni raqamlar bo‘yicha ajratamiz (1), 2), 3)...)
mashqlar = re.split(r"\s+\d+\)\s*", mashq_text)
mashqlar = [m.strip() for m in mashqlar if len(m.strip()) > 30]

if not mashqlar:
    print("❌ Mashqlar topilmadi.")
    exit()

# 7️⃣ Har bir mashqdan bittadan misolni chiqaramiz
print("\n📘 SONLI IFODALAR — Mashqlar:")
for i, mashq in enumerate(mashqlar[:10], start=1):
    first_line = mashq.split(".")[0][:200]
    print(f"\n{i}) {first_line.strip()} ...")
