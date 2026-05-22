# app.py

import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Importa schema e system instruction
from config import RECEITA_SCHEMA, SYSTEM_INSTRUCTION

# =========================================================
# CONFIGURAÇÕES INICIAIS
# =========================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("A variável GEMINI_API_KEY não foi encontrada no .env")

client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)
CORS(app)

# =========================================================
# SEGURANÇA / MODERAÇÃO
# =========================================================

PALAVRAS_PROIBIDAS = [
    # violência
    "matar",
    "assassinar",
    "bomba",
    "terrorismo",
    "arma",
    "violencia",

    # preconceito
    "racismo",
    "nazismo",
    "preconceito",
    "homofobia",

    # sexual
    "sexo",
    "porno",
    "pornografia",
    "estupr",
    "pedofilia",

    # drogas
    "cocaina",
    "maconha",
    "droga",
    "crack",

    # automutilação
    "suicidio",
    "automutilacao",

    # crimes
    "hackear",
    "crime",

    # jailbreak
    "ignore previous instructions",
    "ignore all instructions",
    "developer mode",
    "dan mode",
    "jailbreak",
    "system instruction",
    "prompt injection"
]

def contem_conteudo_proibido(texto):
    texto = texto.lower()

    for palavra in PALAVRAS_PROIBIDAS:
        if palavra in texto:
            return True

    return False

# =========================================================
# GERAÇÃO DA RECEITA
# =========================================================

def generate_recipe(ingredientes):

    lista_ingredientes = ", ".join(ingredientes)

    conteudo_prompt = f"""
    Crie uma receita utilizando obrigatoriamente estes ingredientes:
    {lista_ingredientes}
    """

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=conteudo_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=RECEITA_SCHEMA,
            temperature=0.6,
            max_output_tokens=1200
        )
    )

    return response.text

# =========================================================
# ROTAS
# =========================================================

@app.route("/")
def root():
    return jsonify({
        "status": "success",
        "message": "API Gerador de Receitas funcionando!",
        "version": "2.0"
    }), 200

@app.route("/generate", methods=["POST"])
def generate():

    try:
        data = request.get_json()

        # =================================================
        # VALIDAÇÃO DO JSON
        # =================================================

        if not data:
            return jsonify({
                "status": "error",
                "message": "JSON não enviado."
            }), 400

        if "ingredientes" not in data:
            return jsonify({
                "status": "error",
                "message": "O campo 'ingredientes' é obrigatório."
            }), 400

        ingredientes = data.get("ingredientes")

        # =================================================
        # VALIDAÇÃO DA LISTA
        # =================================================

        if not isinstance(ingredientes, list):
            return jsonify({
                "status": "error",
                "message": "Ingredientes devem ser enviados em uma lista."
            }), 400

        if len(ingredientes) < 3:
            return jsonify({
                "status": "error",
                "message": "Você precisa fornecer no mínimo 3 ingredientes."
            }), 400

        # =================================================
        # LIMPEZA DOS DADOS
        # =================================================

        ingredientes = [
            str(item).strip()
            for item in ingredientes
            if str(item).strip()
        ]

        texto_ingredientes = " ".join(ingredientes)

        # =================================================
        # LIMITADOR DE TAMANHO
        # =================================================

        if len(texto_ingredientes) > 300:
            return jsonify({
                "status": "error",
                "message": "Texto muito grande."
            }), 400

        # =================================================
        # MODERAÇÃO DA ENTRADA
        # =================================================

        if contem_conteudo_proibido(texto_ingredientes):
            return jsonify({
                "status": "error",
                "message": "Conteúdo impróprio detectado."
            }), 400

        # =================================================
        # GERAÇÃO DA RECEITA
        # =================================================

        receita_json_string = generate_recipe(ingredientes)

        # =================================================
        # MODERAÇÃO DA RESPOSTA
        # =================================================

        if contem_conteudo_proibido(receita_json_string):
            return jsonify({
                "status": "error",
                "message": "A resposta gerada foi bloqueada por segurança."
            }), 400

        # =================================================
        # CONVERTE JSON
        # =================================================

        receita_estruturada = json.loads(receita_json_string)

        # =================================================
        # RESPOSTA FINAL
        # =================================================

        return jsonify({
            "status": "success",
            "ingredientes_enviados": ingredientes,
            "dados_receita": receita_estruturada
        }), 200

    except json.JSONDecodeError:
        return jsonify({
            "status": "error",
            "message": "Erro ao interpretar o JSON gerado pela IA."
        }), 500

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Erro interno: {str(e)}"
        }), 500

# =========================================================
# EXECUÇÃO
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)