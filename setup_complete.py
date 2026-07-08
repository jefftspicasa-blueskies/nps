# setup_complete.py
import subprocess
import sys
import os

def instalar_dependencias():
    """Instala as dependências necessárias"""
    print("📦 Instalando dependências...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("✅ Dependências instaladas!")

def executar_migration():
    """Executa a migration do banco"""
    print("🔄 Executando migration do banco...")
    subprocess.check_call([sys.executable, "migration.py"])
    print("✅ Migration concluída!")

def iniciar_app():
    """Inicia a aplicação Streamlit"""
    print("🚀 Iniciando aplicação...")
    subprocess.check_call(["streamlit", "run", "app.py"])

def iniciar_admin():
    """Inicia o dashboard administrativo"""
    print("🚀 Iniciando dashboard administrativo...")
    subprocess.check_call(["streamlit", "run", "admin_dashboard.py"])

if __name__ == "__main__":
    print("=" * 50)
    print("🎯 Configuração Completa do Sistema eNPS")
    print("=" * 50)
    
    # Instalar dependências
    instalar_dependencias()
    
    # Executar migration
    executar_migration()
    
    print("\n" + "=" * 50)
    print("✅ Sistema configurado com sucesso!")
    print("\nPara iniciar a aplicação:")
    print("  1. Pesquisa: streamlit run app.py")
    print("  2. Admin: streamlit run admin_dashboard.py")
    print("  3. Teste: streamlit run test_duplicidade.py")
    print("=" * 50)
    
    # Perguntar o que fazer
    opcao = input("\nO que deseja fazer? (1-App, 2-Admin, 3-Teste, 4-Sair): ")
    
    if opcao == "1":
        iniciar_app()
    elif opcao == "2":
        iniciar_admin()
    elif opcao == "3":
        subprocess.check_call(["streamlit", "run", "test_duplicidade.py"])
    else:
        print("Saindo...")