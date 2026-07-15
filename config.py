# config.py
import hashlib
import secrets
from datetime import datetime
import urllib.parse

class Config:
    # ============================================
    # CONFIGURAÇÕES DO BANCO DE DADOS
    # ALTERE AQUI COM SEUS DADOS!
    # ============================================
    DB_HOST = 'tokaido.proxy.rlwy.net'
    DB_PORT = '27106'
    DB_NAME = 'railway'
    DB_USER = 'postgres'
    DB_PASSWORD = 'AApgKSLEDBJzbYaMiNCGVaXcisiIXrII'  # <-- COLOQUE SUA SENHA AQUI
    DB_SCHEMA = 'trusted'
    
    # Configurações de segurança
    SECRET_KEY = secrets.token_hex(32)
    SESSION_EXPIRY = 86400  # 24 horas em segundos
    
    @property
    def DATABASE_URL(self):
        """URL de conexão com o banco de dados"""
        # Escapar caracteres especiais na senha
        password_encoded = urllib.parse.quote_plus(self.DB_PASSWORD)
        
        # Construir a URL sem o parâmetro options problemático
        return f"postgresql://{self.DB_USER}:{password_encoded}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def TABLE_NAME(self):
        """Nome completo da tabela com schema"""
        return f"{self.DB_SCHEMA}.enps_respostas"
    
    @property
    def TABLE_BLOQUEADAS(self):
        """Nome completo da tabela de bloqueios com schema"""
        return f"{self.DB_SCHEMA}.respostas_bloqueadas"
    
    @staticmethod
    def gerar_session_id():
        """Gera um ID de sessão único"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_urlsafe(16)
        return f"{timestamp}_{random_part}"
    
    @staticmethod
    def gerar_cookie_hash(session_id, user_agent):
        """Gera um hash para o cookie baseado na sessão e user agent"""
        data = f"{session_id}:{user_agent}:{Config.SECRET_KEY}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def validar_session_id(session_id):
        """Valida se o session_id tem o formato correto"""
        if not session_id:
            return False
        parts = session_id.split('_')
        if len(parts) != 3:
            return False
        return True

# Criar uma instância global
config = Config()
