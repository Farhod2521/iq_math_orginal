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
    Masalan: "\\(0,8\\)" -> "0.8"
    """
    expr = re.sub(r'\\left|\\right', '', expr)
    expr = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', expr)
    expr = re.sub(r'\\sqrt\{([^}]+)\}', r'sqrt(\1)', expr)
    expr = re.sub(r'\\\(|\\\)|\\\[|\\\]', '', expr)       # \(...\) ni olib tashlaymiz
    expr = re.sub(r'\{,\}', '.', expr)
    expr = re.sub(r'(?<=\d),(?=\d)', '.', expr)          # sonlar orasidagi vergulni nuqtaga
    expr = expr.replace(',', '.')
    expr = expr.replace('\\', '').replace(' ', '')
    return expr

def insert_multiplication(expr):
    return re.sub(r'(\))\(', r')*(', expr)

def is_number(s):
    try:
        float(s)
        return True
    except:
        return False

def advanced_math_check(student_answer, correct_answer):
    """
    Bu funksiya studentning javobi bilan to‘g‘ri javobni solishtiradi.
    Avval clean_latex() orqali tozalaydi va keyin tekshiradi.
    """
    student = insert_multiplication(clean_latex(student_answer))
    correct = insert_multiplication(clean_latex(correct_answer))

    # Son bo'lsa, bevosita float bilan solishtiramiz
    if is_number(student) and is_number(correct):
        return abs(float(student) - float(correct)) < 1e-6

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
        return student_answer.strip().lower() == correct_answer.strip().lower()

# 🔹 YANGI FUNKSIYA
def clean_student_answers_list(answers_list):
    """
    Composite yoki boshqa joydan kelayotgan javoblar ro‘yxatini tozalab beradi.
    Masalan:
    ["\\(0,8\\)", "\\(1,2\\)"] -> ["0.8", "1.2"]
    """
    return [clean_latex(ans) for ans in answers_list]
