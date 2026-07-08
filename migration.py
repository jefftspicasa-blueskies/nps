# migration.py
import psycopg2
from config import Config
import sys

def executar_migration():
    """Executa a migration para adicionar session_id"""
    config = Config()
    
    try:
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
        
        # Verificar se a coluna session_id existe
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_schema = %s 
            AND table_name = 'enps_respostas' 
            AND column_name = 'session_id'
        """, (config.DB_SCHEMA,))
        
        coluna_existe = cursor.fetchone()[0] > 0
        
        if not coluna_existe:
            print("🔄 Adicionando coluna session_id...")
            cursor.execute("""
                ALTER TABLE enps_respostas 
                ADD COLUMN session_id VARCHAR(255)
            """)
            print("✅ Coluna session_id adicionada")
            
            # Adicionar constraint unique
            print("🔄 Adicionando constraint unique...")
            cursor.execute("""
                ALTER TABLE enps_respostas 
                ADD CONSTRAINT unique_response UNIQUE (session_id)
            """)
            print("✅ Constraint unique_response adicionada")
            
            # Criar índice
            print("🔄 Criando índice...")
            cursor.execute("""
                CREATE INDEX idx_enps_session_id 
                ON enps_respostas(session_id)
            """)
            print("✅ Índice idx_enps_session_id criado")
        else:
            print("ℹ️ Coluna session_id já existe")

        # Criar tabela de bloqueios se não existir
        print("🔄 Verificando tabela respostas_bloqueadas...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS respostas_bloqueadas (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255),
                ip VARCHAR(45),
                tentativa_data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                motivo VARCHAR(255),
                user_agent TEXT
            )
        """)
        print("✅ Tabela respostas_bloqueadas verificada/criada")
        
        # Criar índice para bloqueios
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bloqueadas_session 
            ON respostas_bloqueadas(session_id)
        """)
        print("✅ Índice idx_bloqueadas_session criado")
        
        # Mostrar estrutura da tabela
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = 'enps_respostas'
            ORDER BY ordinal_position
        """, (config.DB_SCHEMA,))
        
        print("\n📊 Estrutura atual da tabela enps_respostas:")
        print("-" * 50)
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} (nullable: {row[2]})")
            
        cursor.close()
        conn.close()
        
        print("\n🎉 Migration concluída com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro na migration: {e}")
        if conn:
            conn.close()
        return False

def verificar_duplicatas_existentes():
    """Verifica se há duplicatas na tabela"""
    config = Config()
    
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute(f"SET search_path TO {config.DB_SCHEMA}")
        
        # Verificar se há registros sem session_id
        cursor.execute("""
            SELECT COUNT(*) 
            FROM enps_respostas 
            WHERE session_id IS NULL
        """)
        
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"⚠️ Encontrados {count} registros sem session_id")
            print("🔧 Para corrigir, execute:")
            print("UPDATE trusted.enps_respostas SET session_id = 'legacy_' || id WHERE session_id IS NULL;")
            print("⚠️ Isso pode quebrar a uniqueness se houver duplicatas!")
        else:
            print("✅ Todos os registros têm session_id")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao verificar duplicatas: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando migration do banco de dados...")
    print("=" * 50)
    
    if executar_migration():
        print("\n" + "=" * 50)
        verificar_duplicatas_existentes()
    else:
        print("\n❌ Migration falhou!")
        sys.exit(1)