# test_db.py
from config import Config
import psycopg2

def testar_conexao():
    config = Config()
    
    print("🔍 Testando conexão com o banco de dados...")
    print(f"Host: {config.DB_HOST}")
    print(f"Porta: {config.DB_PORT}")
    print(f"Banco: {config.DB_NAME}")
    print(f"Usuário: {config.DB_USER}")
    print(f"Schema: {config.DB_SCHEMA}")
    
    try:
        # Testar conexão
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        
        print("\n✅ Conexão bem-sucedida!")
        
        # Verificar schema
        with conn.cursor() as cursor:
            cursor.execute(f"SET search_path TO {config.DB_SCHEMA}")
            cursor.execute("SELECT current_schema()")
            current_schema = cursor.fetchone()[0]
            print(f"✅ Schema atual: {current_schema}")
            
            # Verificar tabela
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.tables 
                    WHERE table_schema = '{config.DB_SCHEMA}' 
                    AND table_name = 'enps_respostas'
                )
            """)
            exists = cursor.fetchone()[0]
            if exists:
                print("✅ Tabela 'enps_respostas' encontrada!")
            else:
                print("❌ Tabela 'enps_respostas' NÃO encontrada!")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Erro ao conectar: {e}")
        return False

if __name__ == "__main__":
    testar_conexao()