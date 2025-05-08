from flask import Flask, request, jsonify
from openai import OpenAI
import json

app = Flask(__name__)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
)
# client = OpenAI(
#     base_url="https://openrouter.ai/api/v1",
#     api_key="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",
# )

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
            # model="openai/gpt-4.1",
            messages=[
                {
                    "role": "user",
                    "content": "Savol ishlanish yo'li bilan ihlab ber ketma ketlikda qisqa lo'nda aniq javob ber " + input_text
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
            return jsonify({'result': result_content})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(debug=True)