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
    expr = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', expr)
    expr = re.sub(r'\\sqrt\{([^}]+)\}', r'sqrt(\1)', expr)
    return expr.replace('\\', '').replace(' ', '')

def insert_multiplication(expr):
    # (a)(b) -> (a)*(b)
    expr = re.sub(r'(\))\(', r')*(', expr)
    return expr

def advanced_math_check(student_answer, correct_answer):
    student = insert_multiplication(clean_latex(student_answer))
    correct = insert_multiplication(clean_latex(correct_answer))
    
    vars_student = detect_variables(student)
    vars_correct = detect_variables(correct)
    
    if set(vars_student) != set(vars_correct):
        return False
    
    try:
        expr1 = sp.sympify(student)
        expr2 = sp.sympify(correct)
        
        diff = sp.simplify(expr1 - expr2)
        if diff == 0:
            return True
        
        for _ in range(10):
            values = {sp.Symbol(v): sp.Rational(randprime(1,100)) for v in vars_student}
            val1 = expr1.subs(values)
            val2 = expr2.subs(values)
            if not sp.simplify(val1 - val2) == 0:
                return False
        return True
        
    except Exception as e:
        # Xatolik yuz bersa ifodalar matnini taqqoslash
        return student.lower().strip() == correct.lower().strip()

print(advanced_math_check("\\((c+t)(c-t)\\)", "\\((c-t)(c+t)\\)"))  # True
print(advanced_math_check("\\frac{x+1}{2}", "(x+1)/2"))    # True
print(advanced_math_check("(x+1)(x-1)", "x^2-1"))         # True
print(advanced_math_check("1/2", "0.5"))       # True
