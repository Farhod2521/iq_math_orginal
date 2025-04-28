import json
import requests

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = "sk-7fc7007663c0477ebbce4d8066ed2044"  # Replace with your actual key

headers = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json"
}

# LaTeX input text (same as above)
latex_text = r"""
\begin{minipage}[t]{\linewidth}\centering
1 Yigindini hisoblang

\begin{enumerate}
\def\labelenumi{\arabic{enumi})}
\item
  \(2\frac{1}{4}\)+3\(\frac{1}{4}\)
\item
  6\(\frac{2}{5} + 3\frac{1}{5}\)
\item
  7\(\frac{7}{8} + 5\frac{5}{8}\)
\end{enumerate}
\end{minipage} & \begin{minipage}[t]{\linewidth}\centering
\begin{enumerate}
\def\labelenumi{\arabic{enumi})}
\item
  6
\item
  9\(\frac{3}{5}\)
\item
  13\(\frac{1}{2}\)
\end{enumerate}
\end{minipage} & \begin{minipage}[t]{\linewidth}\centering
\begin{enumerate}
\def\labelenumi{\arabic{enumi}.}
\item
  Вычислите сумму:
\end{enumerate}

\begin{enumerate}
\def\labelenumi{\arabic{enumi})}
\setcounter{enumi}{3}
\item
  \(2\frac{1}{4}\)+3\(\frac{1}{4}\)
\item
  6\(\frac{2}{5} + 3\frac{1}{5}\)
\item
  7\(\frac{7}{8} + 5\frac{5}{8}\)
\end{enumerate}
\end{minipage} & \begin{minipage}[t]{\linewidth}\centering
\begin{enumerate}
\def\labelenumi{\arabic{enumi})}
\setcounter{enumi}{3}
\item
  6
\item
  9\(\frac{3}{5}\)
\item
  13\(\frac{1}{2}\)
\end{enumerate}
\end{minipage} \\
"""
data = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant that converts LaTeX to JSON."},
        {"role": "user", "content": f"Convert the following LaTeX text into a JSON structure:\n\n{latex_text}"}
    ],
    "temperature": 0,
    "max_tokens": 1500
}

try:
    response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
    response.raise_for_status()
    
    json_response = response.json()['choices'][0]['message']['content']
    
    try:
        json_data = json.loads(json_response)
        print(json.dumps(json_data, indent=2))
    except json.JSONDecodeError:
        print("Failed to decode JSON response. Here's the raw text:")
        print(json_response)

except Exception as e:
    print(f"An error occurred: {e}")