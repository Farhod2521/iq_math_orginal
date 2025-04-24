def tozalash(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # & belgilarini olib tashlash
    cleaned_content = content.replace('&', '').strip()

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)

# Foydalanish:
tozalash(r'D:\iq_math_orginal\testdoc\vertopal.com_5.latex', r'D:\iq_math_orginal\testdoc\5_sinf_clean.latex')
