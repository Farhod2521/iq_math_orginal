import sympy as sp
import re
from sympy import randprime

def detect_variables(expr):
    try:
        parsed_expr = sp.sympify(expr)
        return [str(s) for s in parsed_expr.free_symbols]
    except:
        return []

def clean_latex(expr):
    """
    Latex formatidagi stringni oddiy matematik ko‘rinishga keltiradi.
    Masalan: "\\(0,8\\)" -> "0.8" yoki "0,8" saqlanadi
    """
    expr = re.sub(r'\\left|\\right', '', expr)
    expr = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', expr)
    expr = re.sub(r'\\sqrt\{([^}]+)\}', r'sqrt(\1)', expr)
    expr = re.sub(r'\\\(|\\\)|\\\[|\\\]', '', expr)       
    expr = re.sub(r'\{,\}', '.', expr)
    expr = expr.replace('\\', '').replace(' ', '')
    expr = re.sub(r'\\{([^}]+)\\}', r'\1', expr)
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
    Bu funksiya studentning javobi bilan to‘g‘ri javobni solishtiradi.
    Vergul va nuqta bilan yozilgan sonlarni teng deb hisoblaydi.
    """
    student = insert_multiplication(clean_latex(student_answer))
    correct = insert_multiplication(clean_latex(correct_answer))

    # Son bo'lsa, vergullarni nuqtaga almashtirib solishtiramiz
    if is_number(student) and is_number(correct):
        student_clean = student.replace(',', '.')
        correct_clean = correct.replace(',', '.')
        return abs(float(student_clean) - float(correct_clean)) < 1e-6

    try:
        vars_student = detect_variables(student)
        vars_correct = detect_variables(correct)

        if set(vars_student) != set(vars_correct):
            return False

        expr1 = sp.sympify(student)
        expr2 = sp.sympify(correct)

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

    except:
        # String solishtirishda ham vergul/nuqta farqini hisobga olamiz
        student_clean = student_answer.replace(',', '.').strip().lower()
        correct_clean = correct_answer.replace(',', '.').strip().lower()
        return student_clean == correct_clean

def clean_student_answers_list(answers_list):
    """
    Composite yoki boshqa joydan kelayotgan javoblar ro‘yxatini tozalab beradi.
    Asl formatni saqlab qoladi (vergul saqlanadi).
    """
    return [clean_latex(ans) for ans in answers_list]

# 🔹 YANGI FUNKSIYA: Javoblarni solishtirish uchun maxsus funksiya
def compare_answers(student_answer, correct_answer):
    """
    Student va to'g'ri javoblarni solishtiradi
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