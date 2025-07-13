from redis import Redis
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="/home/angel/python/agente_SDR/.env")

redis = Redis(
    host= os.getenv("IP_VPS"),  # Substitua se usar domínio
    port=6379,
    password= os.getenv("SENHA_REDIS"),  # Troque pela senha real
    decode_responses=True
)

try:
    redis.set("gabriel_test", "conectado_com_sucesso")
    valor = redis.get("gabriel_test")
    print("✅ Redis conectado! Valor:", valor)
except Exception as e:
    print("❌ Erro ao conectar no Redis:", e)
