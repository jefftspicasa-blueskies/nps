# reset_total.py
import psycopg2
from config import Config
import streamlit as st

def resetar_total():
    """Apaga TODOS os dados e reinicia as sequências"""
    config = Config()
    
    print("=" * 60)
    print("🗑️  RESET TOTAL DO BANCO DE DADOS")
    print("=" * 60)
    print("\n⚠️  ATENÇÃO: Isso vai apagar TODOS os dados!")
    print("   - Respostas da pesquisa")
    print("   - Tentativas bloqueadas")
    print("   - Todas as sequências")
    print("\n" + "=" * 60)
    
    # Pedir confirmação
    confirm = input("\nDigite 'APAGAR TUDO' para confirmar: ")
    
    if confirm != "APAGAR TUDO":
        print("❌ Operação cancelada.")
        return
    
    try:
        # Conectar ao banco
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Definir schema
        cursor.execute(f"SET search_path TO {config.DB_SCHEMA}")
        
        print("\n🔄 Apagando dados...")
        
        # Apagar dados da tabela de bloqueios (primeiro)
        cursor.execute("TRUNCATE TABLE respostas_bloqueadas CASCADE;")
        print("  ✅ Tabela respostas_bloqueadas limpa")
        
        # Apagar dados da tabela principal
        cursor.execute("TRUNCATE TABLE enps_respostas CASCADE;")
        print("  ✅ Tabela enps_respostas limpa")
        
        # Resetar sequências
        cursor.execute("ALTER SEQUENCE enps_respostas_id_seq RESTART WITH 1;")
        print("  ✅ Sequência enps_respostas_id_seq resetada")
        
        cursor.execute("ALTER SEQUENCE respostas_bloqueadas_id_seq RESTART WITH 1;")
        print("  ✅ Sequência respostas_bloqueadas_id_seq resetada")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("🎉 BANCO DE DADOS RESETADO COM SUCESSO!")
        print("=" * 60)
        print("\n📊 Estatísticas:")
        print("  - Total de respostas: 0")
        print("  - Tentativas bloqueadas: 0")
        print("  - Próximo ID: 1")
        print("\n✅ Pronto para iniciar a pesquisa do zero!")
        
    except Exception as e:
        print(f"\n❌ Erro ao resetar banco: {e}")

if __name__ == "__main__":
    resetar_total()