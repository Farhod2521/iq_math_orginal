# -*- coding: utf-8 -*-
"""advanced_math_check ni Django'siz sinash."""
import io, os, sys, types

BACKEND = r"D:\ISHXONA\iqmath_frontend\iqmath_backend"
sys.path.insert(0, BACKEND)
# Django o'rnatilmagan -> strip_tags ning aynan Django'dagi nusxasi stub qilingan
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "stub"))

import importlib.util
spec = importlib.util.spec_from_file_location(
    "mac", os.path.join(BACKEND, "django_app", "app_student", "math_answer_check.py")
)
mac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mac)

check = mac.advanced_math_check

CASES = [
    # (o'quvchi javobi, bazadagi to'g'ri javob, kutilgan natija, izoh)
    (">", ">", True, "oddiy taqqoslash belgisi"),
    (">", "&gt;", True, "BUG-1: bazada HTML entity"),
    ("<", "&lt;", True, "BUG-1: HTML entity <"),
    (">", "<p>&gt;</p>", True, "CKEditor HTML ichida"),
    ("=", "<p>=</p>", True, "teng belgisi"),
    (">", "<", False, "haqiqatan noto'g'ri"),
    ("\u2265", ">=", True, "BUG-2: unicode >= belgisi"),
    ("\u2264", "<=", True, "BUG-2: unicode <= belgisi"),
    ("-5", "\u22125", True, "BUG-2: unicode minus"),
    ("2*3", "2\u00d73", True, "unicode ko'paytirish"),
    ("0,8", "0.8", True, "vergul/nuqta"),
    ("0.8", "<p>0,8</p>", True, "vergul + HTML"),
    ("2x", "2*x", True, "BUG-3: yashirin ko'paytirish"),
    ("2*x", "2x", True, "BUG-3: teskari yo'nalish"),
    ("2(x+1)", "2x+2", True, "qavsni ochish"),
    ("8^(7)", "2097152", True, "BUG-4: daraja (XOR emas)"),
    ("8<sup>7</sup>", "2097152", True, "BUG-4: HTML sup -> daraja"),
    ("x+1", "1+x", True, "o'rin almashtirish"),
    ("x+1", "x+2", False, "haqiqatan noto'g'ri ifoda"),
    ("1, 2, 3", "1,2,3", True, "probelli ro'yxat"),
    ("  5  ", "5", True, "atrofdagi probellar"),
    ("ABC", "abc", True, "katta-kichik harf"),
    ("5", "", False, "to'g'ri javob bo'sh"),

    # --- ARALASH SON (mixed number) ---
    ("-18\\frac{2}{5}", "-18,4", True, "BUG-5: aralash son (skrinshotdagi holat)"),
    ("\\(-18\\frac{2}{5}\\)", "-18,4", True, "BUG-5: LaTeX o'ramda"),
    ("−18\\frac{2}{5}", "-18,4", True, "BUG-5: unicode minus + aralash son"),
    ("-18,4", "-18\\frac{2}{5}", True, "BUG-5: teskari yo'nalish"),
    ("-18.4", "-18\\frac{2}{5}", True, "BUG-5: nuqtali kasr"),
    ("3\\frac{5}{6}", "23/6", True, "aralash son -> noto'g'ri kasr"),
    ("3 5/6", "23/6", True, "matnli aralash son '3 5/6'"),
    ("-18\\frac{2}{5}", "-18,5", False, "haqiqatan noto'g'ri aralash son"),
    ("-18\\frac{2}{5}", "18,4", False, "ishora noto'g'ri"),
    ("2\\frac{1}{2}", "2.5", True, "aralash son 2 1/2"),
    ("1/2", "0,5", True, "oddiy kasr va o'nlik"),
    ("\\frac{1}{2}", "0,5", True, "LaTeX kasr va o'nlik"),

    # --- NOTO'G'RI JAVOB NOTO'G'RI QOLISHI SHART ---
    ("2/5", "5/2", False, "kasr teskari"),
    ("0.5", "5", False, "vergul o'rni"),
    ("3\\frac{1}{2}", "3\\frac{1}{3}", False, "aralash son maxraji boshqa"),
    ("2x", "3x", False, "koeffitsient boshqa"),
    ("x", "y", False, "o'zgaruvchi boshqa"),
    ("18", "-18", False, "ishora boshqa"),
    ("1,5", "15", False, "vergul yo'qolishi"),
    ("2^3", "6", False, "daraja ko'paytirish emas"),
]

ok = fail = 0
for student, correct, expected, note in CASES:
    try:
        got = check(student, correct)
    except Exception as e:
        got = "XATO: %s" % e
    mark = "OK  " if got == expected else "FAIL"
    if got == expected:
        ok += 1
    else:
        fail += 1
    print("%s | %-22r vs %-22r -> %-5s (kutilgan %-5s)  %s"
          % (mark, student, correct, got, expected, note))

print("\nJami: %d ta OK, %d ta FAIL" % (ok, fail))
sys.exit(1 if fail else 0)
