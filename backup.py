from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langgraph.graph.message import add_messages
import requests
import os
from supabase import Client, create_client
from dotenv import load_dotenv
from langchain.tools import tool
from typing import List
from langchain_core.messages import BaseMessage

load_dotenv(dotenv_path="/home/angel/python/agente_SDR/.env")

# CONEXÂO COM SUPABASE
supabase_url = os.getenv("PROJECT_URL_SUPABASE")
supabase_key = os.getenv("API_KEY_SUPABASE")
supabase: Client = create_client(supabase_url, supabase_key)

# CONEXÃO COM EVOLUTION
base_url_evo = os.getenv("BASE_URL_EVO")
instance_token = os.getenv("API_KEY_EVO") 
url = f"{base_url_evo}/message/sendText/agentei_ia"
headers = {
    "Content-Type": "application/json",
    "apikey": instance_token
}

# CONEXÃO COM A GROQ 
llm_groq = ChatGroq(api_key=os.getenv("GROQ_API_KEY"), model_name="llama3-70b-8192", temperature=0)
prompt_ia=""
with open("/home/angel/python/agente_SDR/prompt_ai.txt", "r", encoding="utf-8") as file:
    prompt_ia = file.read()

def gerar_resumo(mensagens: list) -> SystemMessage:
    system_prompt = "Resuma a conversa abaixo preservando todas as decisões tomadas, informações fornecidas sobre o responsável e o aluno, e o nível de interesse. Não omita dados importantes, apenas resuma os diálogos mantendo o contexto."
    
    messages = [SystemMessage(content=system_prompt)] + mensagens
    resposta = llm_groq.invoke(messages)

    return SystemMessage(content=resposta.content)
    
# Variável global para armazenar o número atual (temporária)
current_numero = None

@tool(description="""
Atualiza o nome do responsável e suas qualificações(sempre em formato JSON) nesse formato:
       {
        "buscando_escola": boolean,
        "motivo_busca": "str",
        "cidade": "str",
        "urgencia": "str",
        "qualificado": boolean,
        "observacoes": "str"
        }
      Use apenas SE tudo for informado.
      NÃO use novamente se os dados já foram salvos.
      Antes de usar essa ferramenta, verifique se os dados do responsável e suas qualificações já foram enviados anteriormente.""")
def tool_atualizar_lead(nome: str, qualificacoes: dict = None) -> str:
    # Vamos pegar o número do contexto global temporariamente
    numero = current_numero

    if qualificacoes is None:
        qualificacoes = {}

    print(f"🔄 Atualizando nome do responsável {numero} para: {nome}")
    
    try:
        atualizar_lead = (
            supabase.table("responsaveis")
            .update({
                "nome": nome,
                "qualificacoes": qualificacoes
                })
            .eq("numero", numero)
            .execute()
        )
        print(f"✅ Nome atualizado: {atualizar_lead}")
        return f"Nome do responsável atualizado para: {nome}"
    except Exception as e:
        print(f"❌ Erro ao atualizar nome: {e}")
        return f"Erro ao atualizar nome: {str(e)}"

@tool(description="""
Cria ou atualiza um aluno no sistema.

Use esta ferramenta apenas quando todos os dados do aluno estiverem disponíveis:
- nome
- idade
- série de interesse
- ano letivo
- pode_ingressar

Não use esta ferramenta se estiver faltando alguma informação.
""")
def tool_criar_atualizar_aluno(nome: str, idade: str, serie_interesse: str, ano_letivo: str, pode_ingressar: bool) -> str:
    # Vamos pegar o número do contexto global temporariamente
    numero = current_numero
    
    print(f"🔍 Buscando aluno para responsável: {numero}")
    
    try:
        busca = (
            supabase.table("alunos")
            .select("id")
            .eq("responsavel_id", numero)
            .execute()
        )
        
        print(f"🔍 Resultado da busca: {busca.data}")

        if busca.data:
            aluno_id = busca.data[0]["id"]
            print(f"🔄 Atualizando aluno ID: {aluno_id}")
            
            resultado = supabase.table("alunos").update({
                "nome": nome,
                "idade": idade,
                "serie_interesse": serie_interesse,
                "ano_letivo": ano_letivo,
                "pode_ingressar": pode_ingressar
            }).eq("id", aluno_id).execute()
            
            print(f"✅ Resultado da atualização: {resultado}")
            return f"Dados do aluno {nome} atualizados com sucesso."
        
        else:
            print(f"➕ Criando novo aluno para responsável: {numero}")
            
            resultado = supabase.table("alunos").insert({
                "nome": nome,
                "idade": idade,
                "serie_interesse": serie_interesse,
                "ano_letivo": ano_letivo,
                "pode_ingressar": pode_ingressar,
                "responsavel_id": numero
            }).execute()
            
            print(f"✅ Resultado da inserção: {resultado}")
            return f"Aluno {nome} criado com sucesso."
            
    except Exception as e:
        print(f"❌ Erro na função criar_atualizar_aluno: {e}")
        return f"Erro ao processar dados do aluno: {str(e)}"

tools = [tool_atualizar_lead, tool_criar_atualizar_aluno]
tool_node = ToolNode(tools)
llm_com_tools = llm_groq.bind_tools(tools)

class Estado(TypedDict):
    mensagem: Annotated[list, add_messages]
    numero: str
    tipo: str
    prompt: Optional[str]

def salvar_lead(state: Estado):
    numero = state["numero"]
    
    try:
        supabase.table("responsaveis").insert({
            "numero": numero,
            "nome": "Lead",
            "canal_origem": "WhatsApp",
            "qualificacoes": {}
        }).execute()
        print(f"✅ Lead {numero} salvo com sucesso")
    except Exception as e:
        print(f"❌ Erro ao salvar lead: {e}")

    return {}

def salvar_mensagem(state: Estado):
    mensagem = state["mensagem"]
    numero = state["numero"]
    tipo = state["tipo"]
    
    if mensagem:
        # Pega apenas a última mensagem para salvar (evita duplicações)
        ultima_mensagem = mensagem[-1]
        conteudo = ultima_mensagem.content

        try:
            supabase.table("chat_ia").insert({
                "session_id": numero,
                "message": {
                    "type": tipo,
                    "content": conteudo,
                },
            }).execute()
            print(f"✅ Mensagem {tipo} salva com sucesso")
        except Exception as e:
            print(f"❌ Erro ao salvar mensagem: {e}")

    return {}

def agente_sdr(state: Estado):
    global current_numero
    current_numero = state['numero'] 

    try:
        resultado = (
            supabase.table("chat_ia")
            .select("message")
            .eq("session_id", current_numero)
            .order("id", desc=False)  
            .execute()
        )
        
        total_mensagens = resultado.data or []
        mensagens_historico = []

        print(f"📚 Recuperando {len(resultado.data)} mensagens do histórico")

        if len(total_mensagens) > 14:
            print(f"📚 Recuperando {len(total_mensagens)} mensagens do histórico")
            mensagens_recentes = total_mensagens[-14:]
            mensagens_antigas = total_mensagens[:-14]

            for msg_data in mensagens_recentes:
                message = msg_data["message"]
            
                if message["type"] == "human":
                    mensagens_historico.append(HumanMessage(content=message["content"]))
                elif message["type"] == "ai":
                    mensagens_historico.append(AIMessage(content=message["content"]))
                elif message["type"] == "tool":
                    mensagens_historico.append(ToolMessage(content=message["content"]))

            resumo = gerar_resumo(mensagens_antigas)
            print("RESUMO:==================== ", resumo)
            historico_completo = [resumo] + mensagens_historico

        else:
            for msg_data in total_mensagens:
                message = msg_data["message"]
          
                if message["type"] == "human":
                    mensagens_historico.append(HumanMessage(content=message["content"]))
                elif message["type"] == "ai":
                    mensagens_historico.append(AIMessage(content=message["content"]))
                elif message["type"] == "tool":
                    mensagens_historico.append(ToolMessage(content=message["content"]))

            historico_completo = mensagens_historico

    except Exception as e:
        print(f"❌ Erro ao recuperar contexto: {e}")
        mensagens_historico = state["mensagem"]
        historico_completo = mensagens_historico

    print("🤖 Agente pensando...")
    print(f"📊 Processando {len(historico_completo)} mensagens no contexto")

    system_prompt = f"{prompt_ia}\n\nIMPORTANTE: O número do responsável é {state['numero']}. Use sempre este número quando chamar as ferramentas."
    
    messages = [SystemMessage(content=system_prompt)] + historico_completo
    response = llm_com_tools.invoke(messages)
    print("Resposta: ==========  ", response.content)

    return {
        "mensagem": [response],
        "tipo": "ai"
    }  

def execute_tools(state: Estado):
    print("🛠️ Executando ferramentas...")
    last_message = state['mensagem'][-1]
    
    response = tool_node.invoke({"messages": [last_message]})
    
    for msg in response["messages"]:
        print(f"🔧 Resultado da ferramenta: {msg.content}")
    
    return {"mensagem": response["messages"]}

def enviar_mensagem(state: Estado):
    mensagem = state["mensagem"]
    numero = state["numero"]

    ultima_mensagem = mensagem[-1]
    texto = ultima_mensagem.content

    payload = {
        "number": numero,
        "text": texto,
        "delay": 2000
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"✅ Mensagem enviada: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem: {e}")

    return {}

def deve_continuar(state: Estado) -> str:
    last_message = state['mensagem'][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        print("🔍 Decisão: Chamar ferramentas.")
        return "tools"
    else:
        print("✅ Decisão: Finalizar e responder.")
        return "end"

def verificar_lead(state: Estado) -> str:
    numero = state["numero"]
    resultado = supabase.table("responsaveis").select("numero").eq("numero", numero).execute()
    
    if resultado.data:
        print(f"✅ Lead {numero} já existe")
        return "existente"
    else:
        print(f"🆕 Novo lead {numero}")
        return "novo"

workflow = StateGraph(Estado)

workflow.add_node("Verificar_lead", lambda state: {})
workflow.add_node("Salvar_lead", salvar_lead)
workflow.add_node("Salvar_mensagem_human", salvar_mensagem)
workflow.add_node("Agente_SDR", agente_sdr)
workflow.add_node("Execute_tools", execute_tools)
workflow.add_node("Enviar_mensagem", enviar_mensagem)
workflow.add_node("Salvar_mensagem_ai", salvar_mensagem)

workflow.set_entry_point("Verificar_lead")

workflow.add_conditional_edges("Verificar_lead", verificar_lead, {
    "novo": "Salvar_lead",
    "existente": "Salvar_mensagem_human"
})

workflow.add_edge("Salvar_lead", "Salvar_mensagem_human")
workflow.add_edge("Salvar_mensagem_human", "Agente_SDR")

workflow.add_conditional_edges("Agente_SDR", deve_continuar, {
    "tools": "Execute_tools",
    "end": "Enviar_mensagem"
})

workflow.add_edge("Execute_tools", "Agente_SDR")
workflow.add_edge("Enviar_mensagem", "Salvar_mensagem_ai")
workflow.add_edge("Salvar_mensagem_ai", END)

grafo = workflow.compile()

if __name__ == "__main__":
    entrada = {
        "numero": "557998760230",
        "mensagem": [HumanMessage(content=str(input("DIGITE: ")))],
        "tipo": "human"
    }

    try:
        saida = grafo.invoke(entrada)
        print("🎉 Processamento concluído!")
            
    except Exception as e:
        print(f"❌ Erro na execução: {e}")