# duplicidade_control.py - Controle de duplicidade em camadas para pesquisa anonima
import streamlit as st
from datetime import datetime
from config import Config
import psycopg2

class DuplicidadeControl:
    """Controla respostas duplicadas mantendo anonimato"""
    
    def __init__(self):
        self.config = Config()
        self.session_key = 'enps_session_id'
        self.cookie_key = 'enps_cookie_hash'
    
    def init_session(self):
        """Inicializa a sessão do usuário se não existir"""
        if self.session_key not in st.session_state:
            # Gerar novo session_id
            session_id = self.config.gerar_session_id()
            st.session_state[self.session_key] = session_id
            
            # Gerar cookie hash
            user_agent = st.query_params.get('user_agent', 'Unknown')
            cookie_hash = self.config.gerar_cookie_hash(session_id, user_agent)
            st.session_state[self.cookie_key] = cookie_hash
            
            # Salvar cookie no navegador (via JavaScript)
            self._set_cookie(cookie_hash)
    
    def _set_cookie(self, cookie_hash):
        """Define cookie no navegador via JavaScript"""
        st.markdown(f"""
        <script>
            document.cookie = "enps_hash={cookie_hash}; path=/; max-age=86400; samesite=lax";
        </script>
        """, unsafe_allow_html=True)

    def _obter_ip_real(self):
        """Obtém IP do usuario sem exigir identificacao pessoal"""
        try:
            if hasattr(st, 'context') and hasattr(st.context, 'ip_address'):
                return st.context.ip_address
        except Exception:
            pass
        return st.query_params.get('ip', '0.0.0.0')

    @staticmethod
    def _ip_prefix(ip):
        """Retorna prefixo de rede para reduzir granularidade e preservar anonimato"""
        if not ip:
            return ''
        if ':' in ip:
            # IPv6: usa os 4 primeiros blocos
            parts = ip.split(':')
            return ':'.join(parts[:4])
        parts = ip.split('.')
        if len(parts) == 4:
            return '.'.join(parts[:3])
        return ip

    @staticmethod
    def _is_valid_fingerprint(fingerprint):
        if not fingerprint:
            return False
        if fingerprint in ['unknown', 'None', '']:
            return False
        return True

    def _registrar_bloqueio(self, motivo, session_id, ip, user_agent):
        """Registra tentativa bloqueada para auditoria"""
        conn = None
        try:
            conn = psycopg2.connect(self.config.DATABASE_URL)
            cursor = conn.cursor()
            query = f"""
            INSERT INTO {self.config.TABLE_BLOQUEADAS} (session_id, ip, motivo, user_agent)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (session_id, ip, motivo, user_agent))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception:
            if conn:
                conn.close()

    def possui_liberacao_manual(self, session_id, ip, user_agent):
        """Verifica se existe liberacao manual temporaria para o acesso"""
        conn = None
        try:
            conn = psycopg2.connect(self.config.DATABASE_URL)
            cursor = conn.cursor()
            query = f"""
            SELECT COUNT(*)
            FROM {self.config.TABLE_BLOQUEADAS}
            WHERE motivo LIKE 'liberacao_manual:%'
              AND tentativa_data >= CURRENT_TIMESTAMP - INTERVAL '2 hours'
              AND (
                    (session_id IS NOT NULL AND session_id <> '' AND session_id = %s)
                 OR ((ip IS NOT NULL AND ip <> '' AND ip = %s)
                     AND (user_agent IS NOT NULL AND user_agent <> '' AND user_agent = %s))
              )
            """
            cursor.execute(query, (session_id or '', ip or '', user_agent or ''))
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return count > 0
        except Exception:
            if conn:
                conn.close()
            return False

    def avaliar_risco_duplicidade(self):
        """Avalia risco de duplicidade por multiplos sinais anonimos"""
        conn = None
        try:
            session_id = st.session_state.get(self.session_key, '')
            fingerprint = st.session_state.get('device_fingerprint', '')
            user_agent = st.query_params.get('user_agent', 'Unknown')
            ip_real = self._obter_ip_real()
            ip_prefix = self._ip_prefix(ip_real)

            conn = psycopg2.connect(self.config.DATABASE_URL)
            cursor = conn.cursor()

            # Janela limitada reduz custo e mantém efetividade para anti-fraude
            query = f"""
            SELECT session_id, device_fingerprint, usuario_ip, user_agent, data_resposta
            FROM {self.config.TABLE_NAME}
            WHERE data_resposta >= CURRENT_TIMESTAMP - INTERVAL '90 days'
            ORDER BY data_resposta DESC
            LIMIT 5000
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            maior_score = 0
            melhor_motivo = ""
            agora = datetime.now()

            for row in rows:
                row_session, row_fp, row_ip, row_ua, row_data = row
                row_score = 0
                sinais = []

                if session_id and row_session and row_session == session_id:
                    row_score = max(row_score, 100)
                    sinais.append('session_id_igual')

                if self._is_valid_fingerprint(fingerprint) and row_fp and row_fp == fingerprint:
                    row_score = max(row_score, 80)
                    sinais.append('fingerprint_igual')

                row_prefix = self._ip_prefix(row_ip)
                if ip_prefix and row_prefix and ip_prefix == row_prefix and user_agent and row_ua and user_agent == row_ua:
                    row_score = max(row_score, 60)
                    sinais.append('ip_prefix_user_agent_igual')

                if ip_prefix and row_prefix and ip_prefix == row_prefix:
                    row_score = max(row_score, 25)
                    sinais.append('ip_prefix_igual')

                if user_agent and row_ua and user_agent == row_ua:
                    row_score = max(row_score, 20)
                    sinais.append('user_agent_igual')

                # Mesmo IP+UA em janela curta indica forte probabilidade de repeticao imediata
                if row_data and ip_prefix and row_prefix == ip_prefix and user_agent and row_ua == user_agent:
                    try:
                        horas = (agora - row_data).total_seconds() / 3600
                        if horas <= 12:
                            row_score = max(row_score, 75)
                            sinais.append('ip_ua_recente_12h')
                    except Exception:
                        pass

                if row_score > maior_score:
                    maior_score = row_score
                    melhor_motivo = ','.join(sinais)

            cursor.close()
            conn.close()

            return {
                'score': maior_score,
                'motivo': melhor_motivo,
                'session_id': session_id,
                'ip': ip_real,
                'user_agent': user_agent
            }

        except Exception:
            if conn:
                conn.close()
            return {
                'score': 0,
                'motivo': 'erro_avaliacao',
                'session_id': st.session_state.get(self.session_key, ''),
                'ip': self._obter_ip_real(),
                'user_agent': st.query_params.get('user_agent', 'Unknown')
            }
    
    def ja_respondeu(self):
        """Verifica se o usuário já respondeu a pesquisa"""
        conn = None
        try:
            # Verificar se existe session_id na sessão
            if self.session_key not in st.session_state:
                return False
            
            session_id = st.session_state[self.session_key]
            
            # Conectar ao banco
            conn = psycopg2.connect(self.config.DATABASE_URL)
            cursor = conn.cursor()
            
            # Verificar se já existe resposta com este session_id
            query = f"""
            SELECT COUNT(*) 
            FROM {self.config.TABLE_NAME} 
            WHERE session_id = %s
            """
            cursor.execute(query, (session_id,))
            count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return count > 0
            
        except Exception as e:
            if conn:
                conn.close()
            print(f"Erro ao verificar duplicidade: {e}")
            # Em caso de erro, permitir resposta
            return False
    
    def validar_cookie(self):
        """Valida se o cookie é consistente com a sessão"""
        try:
            if self.session_key not in st.session_state:
                return True  # Permitir se não tem cookie ainda
            
            session_id = st.session_state[self.session_key]
            cookie_hash = st.session_state.get(self.cookie_key, '')
            user_agent = st.query_params.get('user_agent', 'Unknown')
            
            expected_hash = self.config.gerar_cookie_hash(session_id, user_agent)
            
            # Se não tem cookie hash, considera válido (primeiro acesso)
            if not cookie_hash:
                return True
            
            return cookie_hash == expected_hash
            
        except Exception:
            return True  # Em caso de erro, permitir acesso

def verificar_permissao_resposta():
    """Função de alto nível para verificar se o usuário pode responder"""
    control = DuplicidadeControl()
    
    # Inicializar sessão se necessário
    control.init_session()

    session_id = st.session_state.get(control.session_key, '')
    ip_real = control._obter_ip_real()
    user_agent = st.query_params.get('user_agent', 'Unknown')

    # Bypass manual temporario para destravar um acesso especifico
    if control.possui_liberacao_manual(session_id, ip_real, user_agent):
        return True, "Acesso liberado manualmente"
    
    # Verificar se já respondeu
    if control.ja_respondeu():
        control._registrar_bloqueio(
            "bloqueio_forte:session_id_ja_utilizado",
            session_id,
            ip_real,
            user_agent
        )
        return False, "Você já respondeu esta pesquisa. Cada usuário pode responder apenas uma vez."

    # Avaliacao por score com sinais anonimos
    risco = control.avaliar_risco_duplicidade()
    if risco['score'] >= 70:
        control._registrar_bloqueio(
            f"bloqueio_score:{risco['score']}|{risco['motivo']}",
            risco['session_id'],
            risco['ip'],
            risco['user_agent']
        )
        return False, "Detectamos um acesso muito semelhante a uma resposta recente. Para manter a pesquisa anônima e íntegra, apenas uma resposta por acesso é permitida."
    
    # Verificar validade do cookie (com fallback)
    if not control.validar_cookie():
        # Se cookie inválido, apenas reinicializar a sessão
        control.init_session()
        return True, "Sessão reiniciada"
    
    return True, "Pode responder"