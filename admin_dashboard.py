# admin_dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from config import Config
import psycopg2

st.set_page_config(
    page_title="Dashboard eNPS - Administração",
    page_icon="📊",
    layout="wide"
)

# Verificar autenticação
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False

def autenticar_admin():
    """Autenticação simples para o admin"""
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

def get_data():
    """Busca dados do banco"""
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

if not autenticar_admin():
    st.stop()

# Título
st.title("📊 Dashboard eNPS - 1º Trimestre 2026")
st.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# Carregar dados
df = get_data()
duplicidade_stats = get_duplicidade_stats()

if df.empty:
    st.warning("⚠️ Nenhuma resposta registrada ainda!")
    st.stop()

# Normalizar coluna de área para exibição e filtros
if 'area' in df.columns:
    df['area'] = df['area'].fillna('Não informado').replace('', 'Não informado')
elif 'area_atuacao' in df.columns:
    df['area'] = df['area_atuacao'].fillna('Não informado').replace('', 'Não informado')
else:
    df['area'] = 'Não informado'

# Métricas principais
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "Total de Respostas",
        len(df),
        delta=None
    )

with col2:
    enps_media = df['enps_nota'].mean()
    st.metric(
        "Média eNPS",
        f"{enps_media:.1f}/10",
        delta=f"{enps_media - 5:.1f}" if enps_media != 5 else None
    )

with col3:
    # Calcular eNPS
    promotores = len(df[df['enps_nota'] >= 9])
    detratores = len(df[df['enps_nota'] <= 6])
    enps = ((promotores - detratores) / len(df)) * 100
    st.metric(
        "eNPS",
        f"{enps:.0f}",
        delta=f"{enps:.0f} pontos"
    )

with col4:
    st.metric(
        "Usuários Únicos",
        duplicidade_stats['respostas_unicas'],
        delta=f"{duplicidade_stats['respostas_unicas'] - len(df)}" if duplicidade_stats['respostas_unicas'] != len(df) else None
    )

with col5:
    st.metric(
        "Tentativas Bloqueadas",
        duplicidade_stats['tentativas_bloqueadas'],
        delta="🚫"
    )

st.divider()

# Gráficos
col1, col2 = st.columns(2)

with col1:
    # Distribuição das notas eNPS
    fig = px.histogram(
        df, 
        x='enps_nota',
        nbins=11,
        title='📊 Distribuição das Notas eNPS',
        color_discrete_sequence=['#1f77b4']
    )
    fig.update_layout(
        xaxis_title="Nota (0-10)",
        yaxis_title="Número de Respostas",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    # Categorias eNPS
    categorias = df['categoria_enps'].value_counts()
    fig = px.pie(
        values=categorias.values,
        names=categorias.index,
        title='🎯 Distribuição por Categoria',
        color_discrete_map={
            'Promotor': '#2ecc71',
            'Neutro': '#f39c12',
            'Detrator': '#e74c3c'
        }
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
    # Liderança
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
    # Comunicação
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
    # Reconhecimento
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

# Adicionar filtros
col1, col2, col3, col4 = st.columns(4)
with col1:
    data_inicio = st.date_input(
        "Data Início",
        value=datetime.now() - timedelta(days=30)
    )
with col2:
    data_fim = st.date_input(
        "Data Fim",
        value=datetime.now()
    )
with col3:
    categoria_filter = st.selectbox(
        "Filtrar por Categoria",
        ['Todos', 'Promotor', 'Neutro', 'Detrator']
    )
with col4:
    areas_disponiveis = ['Todas'] + sorted(df['area'].dropna().unique().tolist())
    area_filter = st.selectbox(
        "Filtrar por Área",
        areas_disponiveis
    )

# Aplicar filtros
df_filtrado = df[
    (df['data_resposta'].dt.date >= data_inicio) &
    (df['data_resposta'].dt.date <= data_fim)
]

if categoria_filter != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['categoria_enps'] == categoria_filter]

if area_filter != 'Todas':
    df_filtrado = df_filtrado[df_filtrado['area'] == area_filter]

# Mostrar tabela
st.dataframe(
    df_filtrado[[
        'data_resposta',
        'area',
        'enps_nota',
        'categoria_enps',
        'lideranca_geral',
        'comunicacao_clareza',
        'reconhecimento_geral',
        'session_id'
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
        st.metric(
            "Total de Respostas",
            duplicidade_stats['total_respostas']
        )
    with col2:
        st.metric(
            "Respostas Únicas",
            duplicidade_stats['respostas_unicas']
        )
    with col3:
        taxa_duplicidade = ((duplicidade_stats['total_respostas'] - duplicidade_stats['respostas_unicas']) / 
                           duplicidade_stats['total_respostas'] * 100) if duplicidade_stats['total_respostas'] > 0 else 0
        st.metric(
            "Taxa de Duplicidade",
            f"{taxa_duplicidade:.1f}%",
            delta=f"-{taxa_duplicidade:.1f}%" if taxa_duplicidade > 0 else None
        )
    
    # Tabela de tentativas bloqueadas
    if duplicidade_stats['tentativas_bloqueadas'] > 0:
        st.subheader("🚫 Tentativas Bloqueadas Recentes")
        config = Config()
        conn = psycopg2.connect(config.DATABASE_URL)
        query_bloq = f"""
        SELECT 
            tentativa_data,
            session_id,
            ip,
            motivo
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
    # Botão para recarregar dados
    if st.button("🔄 Recarregar Dados"):
        st.rerun()