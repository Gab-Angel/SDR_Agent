from flask import Flask, request, jsonify
from langchain_core.messages import HumanMessage

from main import grafo
from buffer_redis import adicionar_ao_buffer, iniciar_ouvinte_background
from audio_transcription import audio_transcription

app = Flask(__name__)

mensagens_processadas = set()

async def processar_mensagens_agrupadas(numero: str, texto_final: str):
    
    try:

        hash_mensagem = hash(f"{numero}:{texto_final}")
        
        if hash_mensagem in mensagens_processadas:
            print(f"⚠️ Mensagem duplicada ignorada para {numero}")
            return
        
        mensagens_processadas.add(hash_mensagem)
        
        print(f"📦 Processando buffer para: {numero}")
        print(f"💬 Texto agrupado: {texto_final}")
        
        entrada = {
            "numero": numero,
            "mensagem": [HumanMessage(content=texto_final)],
            "tipo": "human"
        }

        grafo.invoke(entrada)
        
        print(f"✅ Mensagens processadas com sucesso para {numero}")
        
        mensagens_processadas.discard(hash_mensagem)
        
    except Exception as e:
        print(f"❌ Erro ao processar mensagens agrupadas: {e}")

        mensagens_processadas.discard(hash_mensagem)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        dados = request.get_json()
        print(dados)
        messageType = dados['data'].get('messageType')

        if dados:

            if messageType == 'conversation':

                mensagem = dados['data']["message"].get("conversation")
                
            elif messageType == 'audioMessage':

                base64 = dados['data']["message"].get("base64")
                print("Processando Audio...")
                result = audio_transcription(audio_base64=base64)
                mensagem = result["text"]
            
            remoteJid = dados['data']["key"].get("remoteJid")
            numero = remoteJid.split('@')[0]
        
            print(f"📲 Mensagem de: {numero}")
            print(f"💬 Conteúdo: {mensagem}")

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

    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        print("🚀 Iniciando ouvinte de buffer...")
        iniciar_ouvinte_background(processar_mensagens_agrupadas)
    
    print("🌐 Iniciando servidor Flask...")
    app.run(host="0.0.0.0", port=5000, debug=True)