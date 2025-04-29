from openai import OpenAI

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)

completion = client.chat.completions.create(
  model="deepseek/deepseek-r1:free",
  messages=[
    {
      "role": "user",
      "content": "Savol matnini va javoblarini savol_uz, javob_uz, savol_ru, javob_ru nomlari bilan "
                 "JSON formatida yozmoqchiman; har bir savolda sarlavha va bir nechta misol bo'ladi, "
                 "javoblar ham mos tartibda bo'ladi:\n\n"
                 "\\begin{minipage}[t]{\\linewidth}\\centering\n"
                 "1 Yig`indini hisoblang\n"
                 "\\begin{enumerate}\n"
                 "\\def\\labelenumi{\\arabic{enumi})}\n"
                 "\\item\n"
                 "  \(2\\frac{1}{4}\)+3\(\\frac{1}{4}\)\n"
                 "\\item\n"
                 "  6\(\\frac{2}{5} + 3\\frac{1}{5}\)\n"
                 "\\item\n"
                 "  7\(\\frac{7}{8} + 5\\frac{5}{8}\)\n"
                 "\\end{enumerate}\n"
                 "\\end{minipage} & \\begin{minipage}[t]{\\linewidth}\\centering\n"
                 "\\begin{enumerate}\n"
                 "\\def\\labelenumi{\\arabic{enumi})}\n"
                 "\\item\n"
                 "  6\n"
                 "\\item\n"
                 "  9\(\\frac{3}{5}\)\n"
                 "\\item\n"
                 "  13\(\\frac{1}{2}\)\n"
                 "\\end{enumerate}\n"
                 "\\end{minipage} & \\begin{minipage}[t]{\\linewidth}\\centering\n"
                 "\\begin{enumerate}\n"
                 "\\def\\labelenumi{\\arabic{enumi}.}\n"
                 "\\item\n"
                 "  Вычислите сумму:\n"
                 "\\end{enumerate}\n"
                 "\\begin{enumerate}\n"
                 "\\def\\labelenumi{\\arabic{enumi})}\n"
                 "\\setcounter{enumi}{3}\n"
                 "\\item\n"
                 "  \(2\\frac{1}{4}\)+3\(\\frac{1}{4}\)\n"
                 "\\item\n"
                 "  6\(\\frac{2}{5} + 3\\frac{1}{5}\)\n"
                 "\\item\n"
                 "  7\(\\frac{7}{8} + 5\\frac{5}{8}\)\n"
                 "\\end{enumerate}\n"
                 "\\end{minipage} & \\begin{minipage}[t]{\\linewidth}\\centering\n"
                 "\\begin{enumerate}\n"
                 "\\def\\labelenumi{\\arabic{enumi})}\n"
                 "\\setcounter{enumi}{3}\n"
                 "\\item\n"
                 "  6\n"
                 "\\item\n"
                 "  9\(\\frac{3}{5}\)\n"
                 "\\item\n"
                 "  13\(\\frac{1}{2}\)\n"
                 "\\end{enumerate}\n"
                 "\\end{minipage} \\\\"
    }
  ]
)

print(completion.choices[0].message.content)
