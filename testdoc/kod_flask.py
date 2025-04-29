from flask import Flask, request, jsonify
from openai import OpenAI
import json

app = Flask(__name__)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
)

@app.route('/process', methods=['POST'])
def process_text():
    try:
        data = request.get_json()
        input_text = data.get('text', '')
        
        if not input_text:
            return jsonify({'error': 'Matn kiritilmagan'}), 400
        
        # OpenAI API ga so'rov yuborish
        completion = client.chat.completions.create(
            model="deepseek/deepseek-r1:free",
            messages=[
                {
                    "role": "user",
                    "content": "Savol matnini va javoblarini savol_uz, javob_uz, savol_ru, javob_ru nomlari bilan "
                               "JSON formatida yozmoqchiman; har bir savolda sarlavha va bir nechta misol bo'ladi, "
                               "javoblar ham mos tartibda bo'ladi:\n\n" + input_text
                }
            ]
        )
        
        # JSON javobini o'qish
        result_content = completion.choices[0].message.content
        try:
            result_data = json.loads(result_content)
            return jsonify({'result': result_data})
        except json.JSONDecodeError:
            # Agar JSON formatida bo'lmasa, oddiy matn sifatida qaytarish
            return jsonify({'result': [{'savol_uz': input_text, 'javob_uz': result_content}]})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(debug=True)