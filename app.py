from flask import Flask, request, jsonify
from langchain_core.messages import HumanMessage
import asyncio

from main import grafo
from buffer_redis import adicionar_ao_buffer, iniciar_ouvinte_background

app = Flask(__name__)

# Conjunto para rastrear mensagens já processadas (evita duplicação)
mensagens_processadas = set()

async def processar_mensagens_agrupadas(numero: str, texto_final: str):
 
    try:
        # Cria um hash único da mensagem para evitar duplicação
        hash_mensagem = hash(f"{numero}:{texto_final}")
        
        if hash_mensagem in mensagens_processadas:
            print(f"⚠️ Mensagem duplicada ignorada para {numero}")
            return
        
        mensagens_processadas.add(hash_mensagem)
        
        print(f"📦 Processando buffer para: {numero}")
        print(f"💬 Texto agrupado: {texto_final}")
        
        # Cria a entrada para o grafo com o texto final agrupado
        entrada = {
            "numero": numero,
            "mensagem": [HumanMessage(content=texto_final)],
            "tipo": "human"
        }
        
        # Invoca o grafo com as mensagens agrupadas
        grafo.invoke(entrada)
        
        print(f"✅ Mensagens processadas com sucesso para {numero}")
        
        # Remove da lista após processamento bem-sucedido
        mensagens_processadas.discard(hash_mensagem)
        
    except Exception as e:
        print(f"❌ Erro ao processar mensagens agrupadas: {e}")
        # Remove da lista em caso de erro também
        mensagens_processadas.discard(hash_mensagem)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        dados = request.get_json()
        
        if dados:
            mensagem = dados['data']["message"].get("conversation")
            remoteJid = dados['data']["key"].get("remoteJid")
            numero = remoteJid.split('@')[0]

            print(f"📲 Mensagem de: {numero}")
            print(f"💬 Conteúdo: {mensagem}")
            
            # Em vez de processar imediatamente, adiciona ao buffer
            adicionar_ao_buffer(numero, mensagem)
            print(f"➕ Mensagem adicionada ao buffer para {numero}")

            return jsonify({"status": "mensagem adicionada ao buffer"}), 200
        
        else:
            print("⚠️ Payload do webhook não continha os dados esperados.")
            return jsonify({"status": "payload invalido"}), 400

    except Exception as e:
        print(f"❌ Erro no webhook: {e}")
        return jsonify({"status": "erro interno"}), 500

if __name__ == "__main__":
    import os
    
    # Só inicia o ouvinte no processo principal (não no processo de reload do debug)
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        print("🚀 Iniciando ouvinte de buffer...")
        iniciar_ouvinte_background(processar_mensagens_agrupadas)
    
    print("🌐 Iniciando servidor Flask...")
    app.run(host="0.0.0.0", port=5000, debug=True)