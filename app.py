# app.py
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime
import re
import hashlib
import secrets
from config import Config
from duplicidade_control import DuplicidadeControl, verificar_permissao_resposta
from streamlit_javascript import st_javascript

# Configuração da página
st.set_page_config(
    page_title="Pesquisa eNPS - 1º Trimestre 2026",
    page_icon="📊",
    layout="wide"
)


# Inicializar configuração
config = Config()
control = DuplicidadeControl()

AREAS_ATUACAO = [
    "AGRONOMIA",
    "ALMOXARIFADO",
    "CARGAS",
    "COMPRAS",
    "CONTABILIDADE",
    "DADOS",
    "DIRETORIA",
    "E.T.E",
    "ETIQUETA",
    "EXPEDIÇÃO",
    "FATURAMENTO",
    "FINANCEIRO",
    "HIGH CARE - JOSI AMARAL",
    "HIGH CARE - BRUNA CAROLINE",
    "LAVANDERIA",
    "LOW RISK",
    "MANUTENÇÃO",
    "MÁQUINAS",
    "PCP",
    "QUALIDADE",
    "RECEBIMENTO",
    "RESÍDUO",
    "RECURSOS HUMANOS",
    "SEGURANÇA DO TRABALHO",
    "SELEÇÃO"
]

def obter_fingerprint():
    """Obtém uma impressão digital do dispositivo via JavaScript"""
    try:
        # Coleta informações do navegador usando st_javascript
        fingerprint_data = st_javascript("""
            // Coletar informações do navegador
            const data = {
                userAgent: window.navigator.userAgent,
                platform: window.navigator.platform,
                language: window.navigator.language,
                screenWidth: window.screen.width,
                screenHeight: window.screen.height,
                colorDepth: window.screen.colorDepth,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                hardwareConcurrency: window.navigator.hardwareConcurrency || 0,
                deviceMemory: window.navigator.deviceMemory || 0
            };
            
            // Canvas fingerprinting
            const canvas = document.createElement('canvas');
            canvas.width = 256;
            canvas.height = 128;
            const ctx = canvas.getContext('2d');
            ctx.textBaseline = 'top';
            ctx.font = '14px Arial';
            ctx.fillStyle = '#f60';
            ctx.fillRect(125, 1, 62, 20);
            ctx.fillStyle = '#069';
            ctx.fillText('Streamlit eNPS', 2, 15);
            ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
            ctx.fillText('Fingerprint', 4, 45);
            
            // Adicionar formas geométricas para mais complexidade
            ctx.beginPath();
            ctx.arc(50, 50, 30, 0, Math.PI * 2);
            ctx.stroke();
            
            ctx.beginPath();
            ctx.rect(180, 80, 50, 30);
            ctx.fillStyle = 'rgba(255, 0, 0, 0.5)';
            ctx.fill();
            
            data.canvasHash = canvas.toDataURL();
            
            // Gerar hash único
            const json = JSON.stringify(data);
            return btoa(json);
        """)
        
        # Verificar se retornou uma string
        if fingerprint_data and isinstance(fingerprint_data, str):
            return fingerprint_data
        return None
        
    except Exception as e:
        st.warning(f"Não foi possível obter fingerprint: {e}")
        return None

def get_db_connection():
    """Estabelece conexão com o banco de dados PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        
        with conn.cursor() as cursor:
            cursor.execute(f"SET search_path TO {config.DB_SCHEMA}")
        
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

def salvar_respostas(dados):
    """Salva as respostas com fingerprint do dispositivo"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        dados['session_id'] = st.session_state.get('enps_session_id', 'unknown')
        dados['device_fingerprint'] = st.session_state.get('device_fingerprint', 'unknown')
        
        query = f"""
        INSERT INTO {config.TABLE_NAME} (
            enps_nota,
            lideranca_geral,
            lideranca_desenvolvimento,
            lideranca_seguranca,
            lideranca_feedback,
            comunicacao_clareza,
            comunicacao_informacoes,
            reconhecimento_geral,
            reconhecimento_justica,
            reconhecimento_eficacia,
            comentarios_lideranca,
            area,
            usuario_ip,
            user_agent,
            session_id,
            device_fingerprint
        ) VALUES (
            %(enps_nota)s,
            %(lideranca_geral)s,
            %(lideranca_desenvolvimento)s,
            %(lideranca_seguranca)s,
            %(lideranca_feedback)s,
            %(comunicacao_clareza)s,
            %(comunicacao_informacoes)s,
            %(reconhecimento_geral)s,
            %(reconhecimento_justica)s,
            %(reconhecimento_eficacia)s,
            %(comentarios_lideranca)s,
            %(area)s,
            %(usuario_ip)s,
            %(user_agent)s,
            %(session_id)s,
            %(device_fingerprint)s
        )
        """
        cursor.execute(query, dados)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except psycopg2.IntegrityError as e:
        if "unique_response" in str(e):
            st.error("❌ Você já respondeu esta pesquisa. Cada usuário pode responder apenas uma vez.")
        else:
            st.error(f"❌ Erro de integridade: {e}")
        if conn:
            conn.close()
        return False
    except Exception as e:
        st.error(f"❌ Erro ao salvar respostas: {e}")
        if conn:
            conn.close()
        return False

def obter_ip_real():
    """Obtém o IP real do usuário"""
    try:
        if hasattr(st, 'context') and hasattr(st.context, 'ip_address'):
            return st.context.ip_address
    except:
        pass
    return st.query_params.get('ip', '192.168.1.1')

# CSS personalizado
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #1e3d59;
        padding: 20px;
    }
    .section-header {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin: 20px 0 10px 0;
    }
    .stSlider {
        padding: 10px 0;
    }
    .success-message {
        background-color: #d4edda;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin: 20px 0;
    }
    .blocked-message {
        background-color: #f8d7da;
        padding: 40px;
        border-radius: 10px;
        text-align: center;
        margin: 40px 0;
        border: 2px solid #f5c6cb;
    }
    .schema-badge {
        background-color: #4CAF50;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        display: inline-block;
    }
    .anon-badge {
        background-color: #6c757d;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        display: inline-block;
        margin-left: 10px;
    }
    .fingerprint-badge {
        background-color: #17a2b8;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        display: inline-block;
        margin-left: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Inicializar estado de sessão
if 'enps_session_id' not in st.session_state:
    st.session_state['enps_session_id'] = secrets.token_urlsafe(32)

# Tentar obter fingerprint do dispositivo
fingerprint = obter_fingerprint()

if fingerprint and isinstance(fingerprint, str):
    st.session_state['device_fingerprint'] = fingerprint
    fingerprint_status = "✅ Dispositivo identificado"
else:
    # Fallback: usar session_id como fingerprint
    fallback_fingerprint = hashlib.sha256(
        (st.session_state['enps_session_id'] + datetime.now().strftime('%Y%m%d')).encode()
    ).hexdigest()
    st.session_state['device_fingerprint'] = fallback_fingerprint
    fingerprint_status = "ℹ️ Usando identificador de sessão"

# VERIFICAR PERMISSÃO PARA RESPONDER
pode_responder, mensagem = verificar_permissao_resposta()

# Título principal
st.markdown(f"""
    <h1 class='main-title'>
        📊 Pesquisa eNPS - 1º Trimestre 2026 
        <span class='schema-badge'>Schema: {config.DB_SCHEMA}</span>
        <span class='anon-badge'>🔒 Anônimo</span>
        <span class='fingerprint-badge'>{fingerprint_status}</span>
    </h1>
""", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #666;'>Liderança, Comunicação e Reconhecimento</h3>", unsafe_allow_html=True)
st.divider()

# Inicializar estado de sessão
if 'respostas_enviadas' not in st.session_state:
    st.session_state.respostas_enviadas = False

# Verificar se o usuário já respondeu
if not pode_responder:
    st.markdown(f"""
    <div class='blocked-message'>
        <h2>⛔ Acesso Bloqueado</h2>
        <p style='font-size: 18px;'>{mensagem}</p>
        <p style='color: #666; margin-top: 20px;'>
            Esta pesquisa permite apenas uma resposta por usuário para garantir a integridade dos dados.
        </p>
        <p style='color: #999; font-size: 14px; margin-top: 10px;'>
            Se você acredita que isso é um erro, entre em contato com o administrador.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# MOSTRAR MENSAGEM DE SUCESSO SE JÁ ENVIOU
if st.session_state.respostas_enviadas:
    st.markdown("""
    <div class='success-message'>
        <h2>✅ Respostas Enviadas!</h2>
        <p style='font-size: 18px;'>Obrigado por participar da pesquisa!</p>
        <p style='color: #666;'>Suas respostas foram registradas com sucesso.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 Nova Pesquisa"):
        st.session_state.respostas_enviadas = False
        st.rerun()
    
    st.stop()

# Formulário principal
with st.form("enps_form"):
    st.info("🔒 Sua identidade permanece anônima. Esta pesquisa é totalmente confidencial.")

    # Seção 0: Identificação da área
    st.markdown("<div class='section-header'><h3>🏢 Seção 0: Identificação da área</h3></div>", unsafe_allow_html=True)
    area = st.selectbox(
        "Selecione a área em que você atua:",
        options=["Selecione sua área"] + AREAS_ATUACAO,
        key="area"
    )

    st.divider()
    
    # Seção 1: eNPS Geral
    st.markdown("<div class='section-header'><h3>📈 Seção 1: eNPS Geral</h3></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.write("**Pergunta 1**")
        st.info("De 0 a 10, o quanto você recomendaria esta empresa como um bom lugar para trabalhar?")
    with col2:
        enps_nota = st.slider(
            "Nota",
            min_value=0,
            max_value=10,
            value=5,
            step=1,
            key="enps_geral",
            label_visibility="collapsed"
        )
        if enps_nota <= 6:
            st.warning("⚠️ Detrator")
        elif enps_nota <= 8:
            st.info("🔶 Neutro")
        else:
            st.success("✅ Promotor")
    
    st.divider()
    
    # Seção 2: Liderança
    st.markdown("<div class='section-header'><h3>👥 Seção 2: Liderança</h3></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.write("**Pergunta 2**")
        st.caption("Em aspectos gerais (respeito, suporte, comunicação, justiça), como você avalia a postura de seu líder no dia a dia?")
    with col2:
        lideranca_geral = st.slider(
            "Avaliação geral da liderança",
            0, 10, 5, 1,
            key="lideranca_geral",
            label_visibility="collapsed"
        )
        st.caption("0 - Totalmente insatisfatório | 10 - Totalmente satisfatório")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.write("**Pergunta 3**")
        st.caption("O quanto você recomendaria sua liderança como alguém que apoia seu desenvolvimento?")
    with col2:
        lideranca_desenvolvimento = st.slider(
            "Recomendação para desenvolvimento",
            0, 10, 5, 1,
            key="lideranca_desenvolvimento",
            label_visibility="collapsed"
        )
        st.caption("0 - Jamais recomendaria | 10 - Com certeza recomendaria")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.write("**Pergunta 4**")
        st.caption("Segurança para se expressar: Você sente que sua liderança escuta suas opiniões e promove um ambiente seguro para que a equipe se expresse sem julgamentos ou retaliações?")
    with col2:
        lideranca_seguranca = st.slider(
            "Segurança para se expressar",
            0, 10, 5, 1,
            key="lideranca_seguranca",
            label_visibility="collapsed"
        )
        st.caption("0 - Nunca me sinto ouvido | 10 - Sempre me sinto ouvido")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.write("**Pergunta 5**")
        st.caption("Frequência de feedback construtivo: Recebo feedbacks construtivos na frequência adequada")
    with col2:
        lideranca_feedback = st.slider(
            "Frequência de feedback",
            0, 10, 5, 1,
            key="lideranca_feedback",
            label_visibility="collapsed"
        )
        st.caption("0 - Nunca recebo feedback | 10 - Sempre recebo feedback")
    
    st.divider()
    
    # Seção 3: Comunicação
    st.markdown("<div class='section-header'><h3>💬 Seção 3: Comunicação</h3></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.write("**Pergunta 6**")
        st.caption("Clareza e frequência da comunicação: Sua liderança comunica as informações importantes com frequência adequada e de forma clara?")
    with col2:
        comunicacao_clareza = st.slider(
            "Clareza da comunicação",
            0, 10, 5, 1,
            key="comunicacao_clareza",
            label_visibility="collapsed"
        )
        st.caption("0 - Nunca | 10 - Sempre")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.write("**Pergunta 7**")
        st.caption("Informações para desempenho: Recebo as informações necessárias para o desempenho das minhas atividades e tenho clareza sobre as expectativas da empresa em relação ao meu trabalho.")
    with col2:
        comunicacao_informacoes = st.slider(
            "Informações para desempenho",
            0, 10, 5, 1,
            key="comunicacao_informacoes",
            label_visibility="collapsed"
        )
        st.caption("0 - Discordo totalmente | 10 - Concordo totalmente")
    
    st.divider()
    
    # Seção 4: Reconhecimento
    st.markdown("<div class='section-header'><h3>🏆 Seção 4: Reconhecimento</h3></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.write("**Pergunta 8**")
        st.caption("Reconhecimento pelo resultado: Através da liderança sou reconhecido pelo resultado do meu trabalho.")
    with col2:
        reconhecimento_geral = st.slider(
            "Reconhecimento pelo resultado",
            0, 10, 5, 1,
            key="reconhecimento_geral",
            label_visibility="collapsed"
        )
        st.caption("0 - Nunca | 10 - Sempre")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.write("**Pergunta 9**")
        st.caption("Justiça em elogios e correções: Os elogios e correções são realizados de forma justa e imparcial?")
    with col2:
        reconhecimento_justica = st.slider(
            "Justiça em elogios",
            0, 10, 5, 1,
            key="reconhecimento_justica",
            label_visibility="collapsed"
        )
        st.caption("0 - Nunca | 10 - Sempre")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.write("**Pergunta 10**")
        st.caption("Eficácia do reconhecimento: Sinto que a forma com que meu trabalho é reconhecido é eficaz e justo.")
    with col2:
        reconhecimento_eficacia = st.slider(
            "Eficácia do reconhecimento",
            0, 10, 5, 1,
            key="reconhecimento_eficacia",
            label_visibility="collapsed"
        )
        st.caption("0 - Nunca | 10 - Sempre")
    
    st.divider()
    
    # Seção 5: Comentários abertos
    st.markdown("<div class='section-header'><h3>✍️ Seção 5: Comentários</h3></div>", unsafe_allow_html=True)
    
    comentarios_lideranca = st.text_area(
        "Minhas considerações em aspectos gerais em relação à liderança:",
        placeholder="Compartilhe sua opinião sobre a liderança, comunicação e reconhecimento...",
        height=150
    )
    
    st.divider()
    
    # Botão de submissão do formulário
    submitted = st.form_submit_button("📤 Enviar Respostas", use_container_width=True)
    
    if submitted:
        if area == "Selecione sua área":
            st.error("❌ Selecione a área em que você atua para enviar a pesquisa.")
        else:
            respostas = {
                'enps_nota': enps_nota,
                'lideranca_geral': lideranca_geral,
                'lideranca_desenvolvimento': lideranca_desenvolvimento,
                'lideranca_seguranca': lideranca_seguranca,
                'lideranca_feedback': lideranca_feedback,
                'comunicacao_clareza': comunicacao_clareza,
                'comunicacao_informacoes': comunicacao_informacoes,
                'reconhecimento_geral': reconhecimento_geral,
                'reconhecimento_justica': reconhecimento_justica,
                'reconhecimento_eficacia': reconhecimento_eficacia,
                'comentarios_lideranca': comentarios_lideranca,
                'area': area,
                'usuario_ip': obter_ip_real(),
                'user_agent': st.query_params.get('user_agent', 'Streamlit App')
            }
            
            if salvar_respostas(respostas):
                st.session_state.respostas_enviadas = True
                st.rerun()

# Sidebar com informações
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/rating.png", width=80)
    st.title("ℹ️ Informações")
    st.markdown("---")
    st.markdown(f"""
    **📋 Sobre a pesquisa**
    
    Esta pesquisa avalia:
    - 👥 Liderança
    - 💬 Comunicação  
    - 🏆 Reconhecimento
    
    **⏱️ Tempo estimado:** 3-5 minutos
    
    **🔒 Privacidade:** 
    Suas respostas são anônimas e confidenciais.
    
    **🛡️ Resposta única:**
    Cada usuário pode responder apenas uma vez.
    
    **🗄️ Schema:** `{config.DB_SCHEMA}`
    
    **🖥️ Status:** {fingerprint_status}
    """)
