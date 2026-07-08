# monitor.py
import psycopg2
from config import Config
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

def monitorar_atividade():
    config = Config()
    conn = psycopg2.connect(config.DATABASE_URL)
    cursor = conn.cursor()
    
    # Verificar atividade nas últimas 24h
    query = f"""
    SELECT COUNT(*) 
    FROM {config.TABLE_NAME}
    WHERE data_resposta > NOW() - INTERVAL '24 hours'
    """
    cursor.execute(query)
    respostas_24h = cursor.fetchone()[0]
    
    # Verificar tentativas bloqueadas
    query_bloq = f"""
    SELECT COUNT(*) 
    FROM {config.TABLE_BLOQUEADAS}
    WHERE tentativa_data > NOW() - INTERVAL '24 hours'
    """
    cursor.execute(query_bloq)
    bloqueios_24h = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    return {
        'respostas_24h': respostas_24h,
        'bloqueios_24h': bloqueios_24h,
        'timestamp': datetime.now()
    }

if __name__ == "__main__":
    stats = monitorar_atividade()
    print(f"📊 Atividade nas últimas 24h:")
    print(f"  - Respostas: {stats['respostas_24h']}")
    print(f"  - Bloqueios: {stats['bloqueios_24h']}")