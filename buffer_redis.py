import redis
import json
import asyncio
from typing import Callable, Awaitable
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="/home/angel/python/agente_SDR/.env")

# --- Configurações ---
# Use suas variáveis de ambiente para conectar
redis_client = redis.Redis(host=os.getenv("IP_VPS"), port=6379, password=os.getenv("SENHA_REDIS"), db=0, decode_responses=True)
BUFFER_TIMEOUT = 10  # segundos

# --- Parte 1: Função que recebe e agrupa as mensagens (seu "push buffer1") ---
def adicionar_ao_buffer(numero: str, nova_mensagem: str):
    chave_conteudo = f"buffer:content:{numero}"
    chave_gatilho = f"buffer:trigger:{numero}"

    # Pega o buffer atual ou cria um novo
    mensagens_json = redis_client.get(chave_conteudo)
    mensagens = json.loads(mensagens_json) if mensagens_json else []
    
    mensagens.append(nova_mensagem)

    # Salva o conteúdo e reinicia o timer no gatilho
    redis_client.set(chave_conteudo, json.dumps(mensagens))
    redis_client.setex(chave_gatilho, BUFFER_TIMEOUT, 1)

# --- Parte 2: O processo que age após o timeout (seus "Wait", "If", "Edit Fields" e "Delete") ---
async def ouvinte_de_expiracao(callback: Callable[[str, str], Awaitable[None]]):
    """
    Ouve os eventos de expiração do Redis de forma eficiente.
    Lembre-se de configurar o Redis com: CONFIG SET notify-keyspace-events Ex
    """
    print(">>> Ouvinte de expiração iniciado...")
    pubsub = redis_client.pubsub()
    pubsub.subscribe(f"__keyevent@{redis_client.connection_pool.connection_kwargs['db']}__:expired")

    while True:
        mensagem = pubsub.get_message(ignore_subscribe_messages=True)
        if mensagem and mensagem['data'].startswith("buffer:trigger:"):
            # Extrai o número da chave do gatilho que expirou
            numero = mensagem['data'].split(":")[2]
            chave_conteudo = f"buffer:content:{numero}"
            
            # Pega as mensagens agrupadas
            mensagens_json = redis_client.get(chave_conteudo)
            if mensagens_json:
                # Junta tudo em um texto só (seu "Edit Fields")
                mensagens_lista = json.loads(mensagens_json)
                texto_final = "\n".join(mensagens_lista) # Usando \n como no seu exemplo
                
                # Chama a função principal do seu agente
                await callback(numero, texto_final)
                
                # Limpa o buffer (seu "Redis1 delete")
                redis_client.delete(chave_conteudo)
        
        await asyncio.sleep(0.01)

# --- Exemplo de como você usaria isso ---
async def enviar_para_agente_ia(numero: str, texto: str):
    """
    Esta é a função final que realmente faz o trabalho.
    """
    print("\n" + "="*50)
    print(f"ENVIANDO PARA O AGENTE | NÚMERO: {numero}")
    print(f"TEXTO FINAL: \n{texto}")
    print("="*50)

# Para rodar, você iniciaria o ouvinte como uma tarefa de background
# e chamaria adicionar_ao_buffer a cada mensagem recebida.
# asyncio.create_task(ouvinte_de_expiracao(enviar_para_agente_ia))
