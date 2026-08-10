import html as _html
import sympy as sp
import re
from sympy import randprime
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)
from django.utils.html import strip_tags

_SYMPY_TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

# Matematik belgilarning Unicode variantlari -> ASCII ekvivalenti.
# O'quvchi matematik klaviatura yoki nusxa-ko'chirish orqali kiritganda
# "−" (U+2212) kabi belgilar keladi va ular oddiy "-" bilan teng emas edi.
UNICODE_MATH_MAP = {
    # Minus va tire variantlari
    "\u2212": "-",   # MINUS SIGN
    "\u2010": "-", "\u2011": "-", "\u2012": "-",
    "\u2013": "-", "\u2014": "-",   # en dash, em dash
    # Ko'paytirish
    "\u00d7": "*",   # MULTIPLICATION SIGN
    "\u22c5": "*", "\u2219": "*", "\u00b7": "*",   # dot operator
    # Bo'lish
    "\u00f7": "/", "\u2215": "/",
    # Taqqoslash
    "\u2264": "<=", "\u2265": ">=",
    "\u2260": "!=",
    "\u2261": "=",
    "\u02c2": "<", "\u02c3": ">",
    "\u2039": "<", "\u203a": ">",
    "\uff1c": "<", "\uff1e": ">", "\uff1d": "=",   # fullwidth
    # Tirnoqlar
    "\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
    # Turli probellar -> oddiy probel / bo'shliq
    "\u00a0": " ", "\u2007": " ", "\u2009": " ",
    "\u202f": " ", "\u200b": "", "\ufeff": "",
}


def normalize_symbols(s):
    """Unicode matematik belgilarni ASCII ko'rinishga keltiradi."""
    if not s:
        return s
    for src, dst in UNICODE_MATH_MAP.items():
        s = s.replace(src, dst)
    return s


def html_to_math_text(s):
    """
    CKEditor (RichTextField) orqali kiritilgan HTML matnni matematik
    belgilarga aylantiradi: "8<sup>7</sup>" -> "8^(7)", "x<sub>1</sub>" -> "x_(1)".
    Bu konvertatsiya strip_tags() dan OLDIN bajarilishi shart — aks holda
    daraja/indeks belgisi yo'qolib, "8<sup>7</sup>" oddiy "87" ga aylanib qoladi.
    """
    if not s:
        return s
    s = s.replace('&nbsp;', ' ').replace('\xa0', ' ')
    s = re.sub(r'<sup[^>]*>(.*?)</sup>', r'^(\1)', s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r'<sub[^>]*>(.*?)</sub>', r'_(\1)', s, flags=re.IGNORECASE | re.DOTALL)
    s = strip_tags(s)
    # MUHIM: strip_tags HTML entity larni faqat matnda tag bo'lsa ochadi.
    # Ya'ni "<p>&gt;</p>" -> ">" bo'ladi, lekin yalang "&gt;" o'zgarishsiz qoladi.
    # Shu sababli o'quvchining ">" javobi bazadagi "&gt;" bilan teng emas deb
    # hisoblanardi. unescape() ni har doim o'zimiz chaqiramiz.
    s = _html.unescape(s)
    return normalize_symbols(s)

def safe_sympify(expr):
    """
    Ifodani sympy ga o'giradi.
      - implicit_multiplication_application: "2x" -> 2*x, "xy" -> x*y.
        Ilgari oddiy sympify() "2x" ni tahlil qila olmay, "2x" va "2*x"
        javoblari teng emas deb hisoblanardi.
      - convert_xor: "^" ni daraja deb tushunadi. sympify() da bu sozlama
        sukut bo'yicha yoqiq, parse_expr() da esa YO'Q — shuning uchun uni
        oshkora qo'shamiz, aks holda html_to_math_text yasagan "8^(7)"
        (ya'ni "8<sup>7</sup>") XOR sifatida hisoblanib qolardi.
    """
    return parse_expr(expr, transformations=_SYMPY_TRANSFORMS)


def decimal_comma_to_dot(s):
    """
    Faqat raqamlar orasidagi vergulni o'nlik nuqtaga aylantiradi:
        "-18,4" -> "-18.4"
    "1,2,3" kabi ro'yxatlar "1.2.3" bo'lib tahlil qilinmaydi va pastdagi
    matnli solishtirishga tushadi — bu to'g'ri xatti-harakat.
    """
    if not s:
        return s
    return re.sub(r'(?<=\d),(?=\d)', '.', s)


def detect_variables(expr):
    try:
        parsed_expr = safe_sympify(expr)
        return [str(s) for s in parsed_expr.free_symbols]
    except Exception:
        return None  # tahlil qilib bo'lmadi (None != bo'sh ro'yxat)

def clean_latex(expr):
    """
    Latex formatidagi stringni oddiy matematik ko'rinishga keltiradi.
    Masalan:
        "\\(0,8\\)" -> "0,8"
        "\\(<\\)"   -> "<"
        "\\(x \\le 5\\)" -> "x<=5"
    """

    if not expr:
        return expr


    expr = re.sub(r'\\left|\\right', '', expr)
    expr = re.sub(r'\\\(|\\\)|\\\[|\\\]', '', expr)

    # ── ARALASH SON (mixed number) ──────────────────────────────────────────
    # "3\frac{5}{6}" = 3 + 5/6,  "-18\frac{2}{5}" = -(18 + 2/5) = -18.4
    # Bu \frac ni oddiy bo'linmaga aylantirishdan OLDIN bajarilishi shart,
    # aks holda "18(2)/(5)" hosil bo'lib, yashirin ko'paytirish tufayli
    # 18 * 2/5 = 7.2 deb noto'g'ri hisoblanardi.
    expr = re.sub(
        r'(\d+)\s*\\frac\{([^{}]+)\}\{([^{}]+)\}',
        r'(\1+(\2)/(\3))',
        expr,
    )
    # Matn ko'rinishidagi aralash son: "3 5/6" -> (3+(5)/(6)).
    # Probellar olib tashlanishidan OLDIN bajariladi, aks holda "35/6" bo'lardi.
    expr = re.sub(r'(\d+)\s+(\d+)\s*/\s*(\d+)', r'(\1+(\2)/(\3))', expr)

    expr = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', expr)
    expr = re.sub(r'\\sqrt\{([^}]+)\}', r'sqrt(\1)', expr)
    expr = expr.replace(r'\le', '<=')
    expr = expr.replace(r'\ge', '>=')
    expr = expr.replace(r'\lt', '<')
    expr = expr.replace(r'\gt', '>')
    expr = expr.replace('\\', '')
    # Klaviaturadagi "×" (ko'paytirish belgisi, U+00D7) ni "*" ga aylantiramiz.
    # Bu o'zgaruvchi sifatidagi "x" harfidan farqli belgi, shuning uchun xavfsiz.
    expr = expr.replace('×', '*')
    expr = expr.replace(' ', '')
    return expr

def insert_multiplication(expr):
    return re.sub(r'(\))\(', r')*(', expr)

def is_number(s):
    try:
        # Vergul bilan yozilgan sonlarni ham qabul qilish
        s_clean = s.replace(',', '.')
        float(s_clean)
        return True
    except:
        return False

def advanced_math_check(student_answer, correct_answer):
    """
    Bu funksiya studentning javobi bilan to"g'ri javobni solishtiradi."
    Vergul va nuqta bilan yozilgan sonlarni teng deb hisoblaydi.
    """
    if student_answer is None or correct_answer is None:
        return False

    student_answer = html_to_math_text(str(student_answer))
    correct_answer = html_to_math_text(str(correct_answer))

    student = insert_multiplication(clean_latex(student_answer))
    correct = insert_multiplication(clean_latex(correct_answer))

    # 1) Aynan bir xil matn — eng arzon va eng ishonchli tekshiruv.
    #    "<", ">", "=" kabi sympy tahlil qila olmaydigan javoblar shu yerda hal bo'ladi.
    if student.strip().lower() == correct.strip().lower():
        return True

    # 2) Son bo'lsa, vergullarni nuqtaga almashtirib solishtiramiz
    if is_number(student) and is_number(correct):
        student_clean = student.replace(',', '.')
        correct_clean = correct.replace(',', '.')
        return abs(float(student_clean) - float(correct_clean)) < 1e-6

    # 3) Simvolik (sympy) taqqoslash — "2(x+1)" va "2x+2" kabilar uchun.
    # Sympy vergulni o'nlik ajratgich deb tushunmaydi ("-18,4" ni juftlik deb
    # o'qiydi), shuning uchun bu bosqichda nuqtaga aylantiramiz.
    student_expr = decimal_comma_to_dot(student)
    correct_expr = decimal_comma_to_dot(correct)

    try:
        vars_student = detect_variables(student_expr)
        vars_correct = detect_variables(correct_expr)

        # detect_variables None qaytarsa, sympy tomonni tahlil qila olmadi.
        # Bunday holda darhol False qaytarmaymiz — 4-bosqichga tushamiz,
        # aks holda tahlil qilinmaydigan to'g'ri javob ham noto'g'ri bo'lardi.
        if vars_student is None or vars_correct is None:
            raise ValueError("sympy tahlil qila olmadi")

        if set(vars_student) != set(vars_correct):
            raise ValueError("o'zgaruvchilar to'plami mos emas")

        expr1 = safe_sympify(student_expr)
        expr2 = safe_sympify(correct_expr)

        # Ikkala tomon ham sof son bo'lsa, kichik yaxlitlash farqini hisobga
        # olib solishtiramiz. Aks holda Rational(-92/5) va Float(-18.4) ayirmasi
        # nolga teng chiqmay, to'g'ri javob noto'g'ri deb belgilanardi.
        if not expr1.free_symbols and not expr2.free_symbols:
            try:
                return abs(float(expr1) - float(expr2)) < 1e-9
            except (TypeError, ValueError):
                pass

        diff = sp.simplify(expr1 - expr2)
        if diff == 0:
            return True

        for _ in range(10):
            values = {sp.Symbol(v): sp.Rational(randprime(1, 100)) for v in vars_student}
            val1 = expr1.subs(values)
            val2 = expr2.subs(values)
            if not sp.simplify(val1 - val2) == 0:
                return False

        return True

    except Exception:
        pass

    # 4) Oxirgi chora: vergul/nuqta farqini yo'qotib matnli solishtirish.
    # `student`/`correct` ishlatiladi (clean_latex'dan o'tgan, probelsiz) -
    # `student_answer`/`correct_answer`da probel saqlanib qolgani uchun
    # "1, 2, 3" va "1,2,3" kabi ro'yxat javoblari noto'g'ri deb chiqib qolardi.
    student_clean = student.replace(',', '.').strip().lower()
    correct_clean = correct.replace(',', '.').strip().lower()
    return student_clean == correct_clean

def clean_student_answers_list(answers_list):
    """
    Composite yoki boshqa joydan kelayotgan javoblar ro'yxatini tozalab beradi.
    Asl formatni saqlab qoladi (vergul saqlanadi).
    """
    return [clean_latex(ans) for ans in answers_list]

# 🔹 YANGI FUNKSIYA: Javoblarni solishtirish uchun maxsus funksiya
def compare_answers(student_answer, correct_answer):
    """
    Student va to"g'ri javoblarni solishtiradi"
    """
    # 1. Avval clean_latex orqali tozalab olamiz
    student_clean = clean_latex(str(student_answer))
    correct_clean = clean_latex(str(correct_answer))
    
    # 2. Sonlarni tekshirish
    if is_number(student_clean) and is_number(correct_clean):
        student_num = student_clean.replace(',', '.')
        correct_num = correct_clean.replace(',', '.')
        return abs(float(student_num) - float(correct_num)) < 1e-6
    
    # 3. Advanced math check (agar murakkab ifodalar bo'lsa)
    try:
        return advanced_math_check(student_clean, correct_clean)
    except:
        # 4. Oddiy string solishtirish
        student_final = student_clean.replace(',', '.').strip().lower()
        correct_final = correct_clean.replace(',', '.').strip().lower()
        return student_final == correct_final

# 🔹 TEST QILISH
if __name__ == "__main__":
    # Test holatlari
    test_cases = [
        ("0,8", "0.8", True),
        ("0.8", "0,8", True),
        ("1,25", "1.25", True),
        ("0,8", "0.9", False),
        ("\\(0,8\\)", "0.8", True),
        ("\\(0,8\\)", "0,8", True)
    ]
    
    for student, correct, expected in test_cases:
        result = compare_answers(student, correct)
        print(f"Student: '{student}' vs Correct: '{correct}' -> {result} (expected: {expected})")