import os
import base64
import json
from groq import Groq

def parse_groq_json(raw_text):
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "itens" in data:
            return data["itens"]
        return data
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        return []

def analyze_receipt_or_list_with_groq(image_path):
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY não configurada no .env")

    client = Groq(api_key=api_key)
    
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text", 
                        "text": "Analise esta imagem, que é uma lista de compras ou recibo de supermercado. Crie uma lista com os itens encontrados. Retorne SOMENTE um JSON Array contendo objetos com 3 chaves: 'nome' (string), 'preco' (float, se não achar ponha 0.0), e 'categoria' (escolha entre 'Mercado', 'Hortifruti', 'Limpeza', 'Açougue' ou 'Outros'). Exporte o array puro, sem formatação markdown (sem graves) e sem chaves raiz."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_string}",
                        },
                    },
                ],
            }
        ],
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        temperature=0.1
    )
    
    result = chat_completion.choices[0].message.content
    print("GROQ RAW RESULT:", result)
    return parse_groq_json(result)
