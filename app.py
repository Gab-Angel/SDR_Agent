from flask import Flask, request, jsonify
from langchain_core.messages import HumanMessage

from main import grafo

app = Flask(__name__)

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
 
            entrada = {
                "numero": numero,
                "mensagem": [HumanMessage(content=mensagem)],
                "tipo": "human"
            }

            config = {"configurable": {"thread_id": numero}}

            grafo.invoke(entrada, config=config)

            return jsonify({"status": "mensagem recebida com sucesso"}), 200
        
        else:
            print("⚠️ Payload do webhook não continha os dados esperados.")
            return jsonify({"status": "payload invalido"}), 400

    except Exception as e:
        print(f"❌ Erro no webhook: {e}")
        return jsonify({"status": "erro interno"}), 500

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5000, debug=True)