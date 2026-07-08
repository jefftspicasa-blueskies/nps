# diagnostico.py
import sys
import subprocess

print("=" * 60)
print("🔍 DIAGNÓSTICO DO AMBIENTE PYTHON")
print("=" * 60)

# 1. Informações do Python
print(f"\n📌 Python versão: {sys.version}")
print(f"📌 Python executável: {sys.executable}")
print(f"📌 Python path: {sys.path}")

# 2. Verificar pacotes instalados
print("\n📦 Pacotes instalados:")
try:
    result = subprocess.run([sys.executable, "-m", "pip", "list"], 
                          capture_output=True, text=True)
    print(result.stdout)
except Exception as e:
    print(f"Erro ao listar pacotes: {e}")

# 3. Tentar importar módulos
print("\n🔌 Testando imports:")
modules = ['streamlit', 'psycopg2', 'dotenv', 'pandas', 'plotly']

for module in modules:
    try:
        __import__(module)
        print(f"  ✅ {module} - OK")
    except ImportError as e:
        print(f"  ❌ {module} - ERRO: {e}")

# 4. Verificar se o dotenv está instalado
print("\n📦 Verificando python-dotenv especificamente:")
try:
    result = subprocess.run([sys.executable, "-m", "pip", "show", "python-dotenv"], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ python-dotenv está instalado")
        print(result.stdout)
    else:
        print("❌ python-dotenv NÃO está instalado")
        print("\nPara instalar, execute:")
        print(f"  {sys.executable} -m pip install python-dotenv")
except Exception as e:
    print(f"Erro ao verificar: {e}")

print("\n" + "=" * 60)
print("Fim do diagnóstico")
print("=" * 60)