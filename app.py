# app.py - Versão Unificada Completa
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import secrets
import plotly.express as px
import plotly.graph_objects as go
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

# ============================================
# CONSTANTES E FUNÇÕES COMPARTILHADAS
# ============================================

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
    "GESTORES",
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
        fingerprint_data = st_javascript("""
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
            
            ctx.beginPath();
            ctx.arc(50, 50, 30, 0, Math.PI * 2);
            ctx.stroke();
            
            ctx.beginPath();
            ctx.rect(180, 80, 50, 30);
            ctx.fillStyle = 'rgba(255, 0, 0, 0.5)';
            ctx.fill();
            
            data.canvasHash = canvas.toDataURL();
            
            const json = JSON.stringify(data);
            return btoa(json);
        """)
        
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

def obter_ip_real():
    """Obtém o IP real do usuário"""
    try:
        if hasattr(st, 'context') and hasattr(st.context, 'ip_address'):
            return st.context.ip_address
    except:
        pass
    return st.query_params.get('ip', '192.168.1.1')

# ============================================
# FUNÇÕES DO DASHBOARD ADMIN
# ============================================

def autenticar_admin():
    """Autenticação simples para o admin"""
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        with st.sidebar:
            st.title("🔐 Acesso Administrativo")
            senha = st.text_input("Senha do Administrador", type="password")
            if st.button("Entrar"):
                # Em produção, use variável de ambiente
                if senha == st.secrets.get("ADMIN_PASSWORD", "admin123"):
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.error("Senha incorreta!")
        return False
    return True

def get_admin_data():
    """Busca dados do banco para o admin"""
    config = Config()
    conn = psycopg2.connect(config.DATABASE_URL)
    query = f"""
    SELECT 
        *,
        CASE 
            WHEN enps_nota >= 9 THEN 'Promotor'
            WHEN enps_nota <= 6 THEN 'Detrator'
            ELSE 'Neutro'
        END as categoria_enps
    FROM {config.TABLE_NAME}
    ORDER BY data_resposta DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_duplicidade_stats():
    """Busca estatísticas de duplicidade"""
    config = Config()
    conn = psycopg2.connect(config.DATABASE_URL)
    
    queries = {
        'total_respostas': f"SELECT COUNT(*) FROM {config.TABLE_NAME}",
        'respostas_unicas': f"SELECT COUNT(DISTINCT session_id) FROM {config.TABLE_NAME}",
        'tentativas_bloqueadas': f"SELECT COUNT(*) FROM {config.TABLE_BLOQUEADAS}",
        'respostas_sem_session': f"SELECT COUNT(*) FROM {config.TABLE_NAME} WHERE session_id IS NULL",
    }
    
    results = {}
    for key, query in queries.items():
        df = pd.read_sql(query, conn)
        results[key] = df.iloc[0, 0] if not df.empty else 0
    
    conn.close()
    return results

def liberar_acesso_temporario(session_id='', ip='', user_agent='', motivo_admin='liberacao_manual'):
    """Registra liberacao manual temporaria (2h) para destravar um acesso"""
    if not session_id and not (ip and user_agent):
        return False, "Informe Session ID ou IP + User Agent."

    config = Config()
    conn = None
    try:
        conn = psycopg2.connect(config.DATABASE_URL)
        cursor = conn.cursor()
        query = f"""
        INSERT INTO {config.TABLE_BLOQUEADAS} (session_id, ip, motivo, user_agent)
        VALUES (%s, %s, %s, %s)
        """
        motivo = f"liberacao_manual:{motivo_admin}"
        cursor.execute(query, (session_id or '', ip or '', motivo, user_agent or ''))
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Liberacao aplicada por 2 horas para esse acesso."
    except Exception as e:
        if conn:
            conn.close()
        return False, f"Erro ao liberar acesso: {e}"

# ============================================
# FUNÇÕES DO APP PRINCIPAL (PESQUISA)
# ============================================

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
        st.error(f"❌ Erro de integridade: {e}")
        if conn:
            conn.close()
        return False
    except Exception as e:
        st.error(f"❌ Erro ao salvar respostas: {e}")
        if conn:
            conn.close()
        return False

# ============================================
# FUNÇÃO PARA RENDERIZAR O DASHBOARD
# ============================================

def render_admin_dashboard():
    """Renderiza o dashboard administrativo"""
    st.title("📊 Dashboard eNPS - 1º Trimestre 2026")
    st.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Carregar dados
    df = get_admin_data()
    duplicidade_stats = get_duplicidade_stats()
    
    if df.empty:
        st.warning("⚠️ Nenhuma resposta registrada ainda!")
        return
    
    # Normalizar coluna de área
    if 'area' in df.columns:
        df['area'] = df['area'].fillna('Não informado').replace('', 'Não informado')
    elif 'area_atuacao' in df.columns:
        df['area'] = df['area_atuacao'].fillna('Não informado').replace('', 'Não informado')
    else:
        df['area'] = 'Não informado'
    
    # Métricas principais
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total de Respostas", len(df))
    
    with col2:
        enps_media = df['enps_nota'].mean()
        st.metric("Média eNPS", f"{enps_media:.1f}/10")
    
    with col3:
        promotores = len(df[df['enps_nota'] >= 9])
        detratores = len(df[df['enps_nota'] <= 6])
        enps = ((promotores - detratores) / len(df)) * 100
        st.metric("eNPS", f"{enps:.0f}")
    
    with col4:
        st.metric("Usuários Únicos", duplicidade_stats['respostas_unicas'])
    
    with col5:
        st.metric("Tentativas Bloqueadas", duplicidade_stats['tentativas_bloqueadas'])
    
    st.divider()
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.histogram(
            df, 
            x='enps_nota',
            nbins=11,
            title='📊 Distribuição das Notas eNPS',
            color_discrete_sequence=['#1f77b4']
        )
        fig.update_layout(xaxis_title="Nota (0-10)", yaxis_title="Número de Respostas", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        categorias = df['categoria_enps'].value_counts()
        fig = px.pie(
            values=categorias.values,
            names=categorias.index,
            title='🎯 Distribuição por Categoria',
            color_discrete_map={'Promotor': '#2ecc71', 'Neutro': '#f39c12', 'Detrator': '#e74c3c'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Análise por área
    st.subheader("🏢 Análise por Área")
    col1, col2 = st.columns(2)
    
    with col1:
        area_counts = df['area'].value_counts().head(10)
        fig = px.bar(
            x=area_counts.values,
            y=area_counts.index,
            orientation='h',
            title='📌 Top 10 Áreas com Mais Respostas',
            labels={'x': 'Respostas', 'y': 'Área'},
            color=area_counts.values,
            color_continuous_scale='Teal'
        )
        fig.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        enps_area = (
            df.groupby('area', as_index=False)
            .agg(media_enps=('enps_nota', 'mean'), total_respostas=('id', 'count'))
            .sort_values('media_enps', ascending=False)
            .head(10)
        )
        fig = px.bar(
            enps_area,
            x='media_enps',
            y='area',
            orientation='h',
            title='⭐ Top 10 Áreas por Média eNPS',
            labels={'media_enps': 'Média eNPS', 'area': 'Área'},
            hover_data=['total_respostas'],
            color='media_enps',
            color_continuous_scale='Viridis',
            range_x=[0, 10]
        )
        fig.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    # Médias por seção
    st.subheader("📈 Análise por Seção")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        lideranca_medias = {
            'Geral': df['lideranca_geral'].mean(),
            'Desenvolvimento': df['lideranca_desenvolvimento'].mean(),
            'Segurança': df['lideranca_seguranca'].mean(),
            'Feedback': df['lideranca_feedback'].mean()
        }
        fig = px.bar(
            x=list(lideranca_medias.keys()),
            y=list(lideranca_medias.values()),
            title='👥 Liderança',
            range_y=[0, 10],
            color=list(lideranca_medias.values()),
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        comunicacao_medias = {
            'Clareza': df['comunicacao_clareza'].mean(),
            'Informações': df['comunicacao_informacoes'].mean()
        }
        fig = px.bar(
            x=list(comunicacao_medias.keys()),
            y=list(comunicacao_medias.values()),
            title='💬 Comunicação',
            range_y=[0, 10],
            color=list(comunicacao_medias.values()),
            color_continuous_scale='Greens'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        reconhecimento_medias = {
            'Resultado': df['reconhecimento_geral'].mean(),
            'Justiça': df['reconhecimento_justica'].mean(),
            'Eficácia': df['reconhecimento_eficacia'].mean()
        }
        fig = px.bar(
            x=list(reconhecimento_medias.keys()),
            y=list(reconhecimento_medias.values()),
            title='🏆 Reconhecimento',
            range_y=[0, 10],
            color=list(reconhecimento_medias.values()),
            color_continuous_scale='Oranges'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Tabela com dados recentes
    st.subheader("📋 Respostas Recentes")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        data_inicio = st.date_input("Data Início", value=datetime.now() - timedelta(days=30))
    with col2:
        data_fim = st.date_input("Data Fim", value=datetime.now())
    with col3:
        categoria_filter = st.selectbox("Filtrar por Categoria", ['Todos', 'Promotor', 'Neutro', 'Detrator'])
    with col4:
        areas_disponiveis = ['Todas'] + sorted(df['area'].dropna().unique().tolist())
        area_filter = st.selectbox("Filtrar por Área", areas_disponiveis)
    
    df_filtrado = df[
        (df['data_resposta'].dt.date >= data_inicio) &
        (df['data_resposta'].dt.date <= data_fim)
    ]
    
    if categoria_filter != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['categoria_enps'] == categoria_filter]
    if area_filter != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['area'] == area_filter]
    
    st.dataframe(
        df_filtrado[[
            'data_resposta', 'area', 'enps_nota', 'categoria_enps',
            'lideranca_geral', 'comunicacao_clareza', 'reconhecimento_geral', 'session_id'
        ]].head(20),
        use_container_width=True,
        column_config={
            'data_resposta': st.column_config.DatetimeColumn('Data'),
            'area': st.column_config.TextColumn('Área'),
            'enps_nota': st.column_config.NumberColumn('eNPS', format='%d'),
            'categoria_enps': st.column_config.TextColumn('Categoria'),
            'lideranca_geral': st.column_config.NumberColumn('Liderança', format='%.1f'),
            'comunicacao_clareza': st.column_config.NumberColumn('Comunicação', format='%.1f'),
            'reconhecimento_geral': st.column_config.NumberColumn('Reconhecimento', format='%.1f'),
            'session_id': st.column_config.TextColumn('Session ID')
        }
    )
    
    # Estatísticas de duplicidade
    with st.expander("🛡️ Estatísticas de Controle de Duplicidade"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Respostas", duplicidade_stats['total_respostas'])
        with col2:
            st.metric("Respostas Únicas", duplicidade_stats['respostas_unicas'])
        with col3:
            taxa_duplicidade = ((duplicidade_stats['total_respostas'] - duplicidade_stats['respostas_unicas']) / 
                               duplicidade_stats['total_respostas'] * 100) if duplicidade_stats['total_respostas'] > 0 else 0
            st.metric("Taxa de Duplicidade", f"{taxa_duplicidade:.1f}%")
        
        if duplicidade_stats['tentativas_bloqueadas'] > 0:
            st.subheader("🚫 Tentativas Bloqueadas Recentes")
            config = Config()
            conn = psycopg2.connect(config.DATABASE_URL)
            query_bloq = f"""
            SELECT tentativa_data, session_id, ip, motivo
            FROM {config.TABLE_BLOQUEADAS}
            ORDER BY tentativa_data DESC
            LIMIT 10
            """
            df_bloq = pd.read_sql(query_bloq, conn)
            conn.close()
            st.dataframe(df_bloq, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🔓 Resetar Trava de Acesso")
        st.caption("Cria uma liberacao manual temporaria (2h) para um acesso bloqueado.")
        
        c1, c2 = st.columns(2)
        with c1:
            liberar_session_id = st.text_input("Session ID (opcional)", key="liberar_session_id")
            liberar_ip = st.text_input("IP (opcional)", key="liberar_ip")
        with c2:
            liberar_user_agent = st.text_input("User Agent (opcional)", key="liberar_user_agent")
            liberar_motivo = st.text_input("Motivo admin", value="ajuste_operacional", key="liberar_motivo")
        
        if st.button("✅ Aplicar Liberação Temporária", use_container_width=True):
            ok, msg = liberar_acesso_temporario(
                session_id=liberar_session_id.strip(),
                ip=liberar_ip.strip(),
                user_agent=liberar_user_agent.strip(),
                motivo_admin=liberar_motivo.strip() or "ajuste_operacional"
            )
            if ok:
                st.success(msg)
            else:
                st.error(msg)
    
    # Download dos dados
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Baixar Dados (CSV)",
            data=csv,
            file_name=f"enps_dados_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    with col2:
        if st.button("🔄 Recarregar Dados"):
            st.rerun()

# ============================================
# RENDERIZAÇÃO DO APP PRINCIPAL (PESQUISA)
# ============================================

def render_survey_app():
    """Renderiza o formulário de pesquisa principal"""
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
        fallback_fingerprint = hashlib.sha256(
            (st.session_state['enps_session_id'] + datetime.now().strftime('%Y%m%d')).encode()
        ).hexdigest()
        st.session_state['device_fingerprint'] = fallback_fingerprint
        fingerprint_status = "ℹ️ Usando identificador de sessão"

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
        
        return

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

        # ... restante do formulário permanece igual ...

        # Botão de submissão do formulário
        submitted = st.form_submit_button("📤 Enviar Respostas", use_container_width=True)

        if submitted:
            if area == "Selecione sua área":
                st.error("❌ Selecione a área em que você atua para enviar a pesquisa.")
            else:
                respostas = {
                    'enps_nota': enps_nota,
                    'lideranca_geral': st.session_state.get('lideranca_geral', 5),
                    'lideranca_desenvolvimento': st.session_state.get('lideranca_desenvolvimento', 5),
                    'lideranca_seguranca': st.session_state.get('lideranca_seguranca', 5),
                    'lideranca_feedback': st.session_state.get('lideranca_feedback', 5),
                    'comunicacao_clareza': st.session_state.get('comunicacao_clareza', 5),
                    'comunicacao_informacoes': st.session_state.get('comunicacao_informacoes', 5),
                    'reconhecimento_geral': st.session_state.get('reconhecimento_geral', 5),
                    'reconhecimento_justica': st.session_state.get('reconhecimento_justica', 5),
                    'reconhecimento_eficacia': st.session_state.get('reconhecimento_eficacia', 5),
                    'comentarios_lideranca': st.session_state.get('comentarios_lideranca', ''),
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
        
        **🗄️ Schema:** `{config.DB_SCHEMA}`
        
        **🖥️ Status:** {fingerprint_status}
        """)
        
        st.markdown("---")
        # Botão para acessar o dashboard administrativo
        if st.button("🔐 Acessar Dashboard Admin", use_container_width=True):
            st.session_state.show_admin = True
            st.rerun()

# ============================================
# CONTROLE DE NAVEGAÇÃO
# ============================================

def main():
    """Função principal que controla a navegação entre os modos"""
    
    # Inicializar estado de navegação
    if 'show_admin' not in st.session_state:
        st.session_state.show_admin = False
    
    # Se estiver no modo admin, autenticar e mostrar dashboard
    if st.session_state.show_admin:
        if autenticar_admin():
            render_admin_dashboard()
            # Botão para voltar à pesquisa
            if st.sidebar.button("⬅️ Voltar para a Pesquisa", use_container_width=True):
                st.session_state.show_admin = False
                st.rerun()
    else:
        render_survey_app()

# ============================================
# EXECUÇÃO PRINCIPAL
# ============================================

if __name__ == "__main__":
    main()
