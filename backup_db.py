# backup_db.py
import psycopg2
import pandas as pd
from datetime import datetime
from config import Config
import os

def fazer_backup():
    config = Config()
    conn = psycopg2.connect(config.DATABASE_URL)
    
    # Backup dos dados
    query = f"SELECT * FROM {config.TABLE_NAME}"
    df = pd.read_sql(query, conn)
    
    # Criar diretório de backup
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    # Salvar backup
    filename = f"{backup_dir}/enps_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False)
    
    conn.close()
    print(f"✅ Backup salvo em: {filename}")
    return filename

if __name__ == "__main__":
    fazer_backup()