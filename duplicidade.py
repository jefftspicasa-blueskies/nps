# test_duplicidade.py
import streamlit as st
from duplicidade_control import DuplicidadeControl, verificar_permissao_resposta

st.set_page_config(
    page_title="Teste de Duplicidade",
    page_icon="🧪"
)

st.title("🧪 Teste do Sistema de Prevenção de Duplicidade")

# Instanciar o controlador
control = DuplicidadeControl()

# Botões de controle
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🔄 Iniciar Nova Sessão"):
        control.resetar_sessao()
        st.rerun()

with col2:
    if st.button("🧹 Limpar Cookies"):
        st.markdown("""
        <script>
            document.cookie = "enps_hash=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
            document.cookie = "enps_session=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        </script>
        """, unsafe_allow_html=True)
        st.success("Cookies limpos! Recarregue a página.")

with col3:
    if st.button("📊 Verificar Status"):
        st.rerun()

st.divider()

# Verificar permissão
pode_responder, mensagem = verificar_permissao_resposta()

# Exibir status
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Status da Sessão")
    st.json({
        "session_id": st.session_state.get('enps_session_id', 'N/A'),
        "cookie_hash": st.session_state.get('enps_cookie_hash', 'N/A'),
        "pode_responder": pode_responder,
        "mensagem": mensagem
    })

with col2:
    st.subheader("🍪 Cookies do Navegador")
    # Tentar ler cookies via JavaScript
    st.markdown("""
    <script>
        function getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        }
        const hash = getCookie('enps_hash');
        document.write(`<p><strong>enps_hash:</strong> ${hash || 'Não encontrado'}</p>`);
        document.write(`<p><strong>enps_session:</strong> ${getCookie('enps_session') || 'Não encontrado'}</p>`);
    </script>
    """, unsafe_allow_html=True)

st.divider()

# Simular ações
st.subheader("🧪 Testes")

if st.button("🔍 Verificar se já respondeu"):
    if control.ja_respondeu():
        st.warning("⚠️ Este usuário JÁ respondeu a pesquisa")
    else:
        st.success("✅ Este usuário AINDA NÃO respondeu a pesquisa")

if st.button("💾 Simular Resposta (para teste)"):
    # Simular que o usuário respondeu
    st.session_state['enps_respondeu'] = True
    st.success("✅ Resposta simulada! Recarregue a página para ver o bloqueio.")
    st.info("Para resetar, clique em 'Iniciar Nova Sessão'")

st.divider()

# Informações adicionais
with st.expander("ℹ️ Como funciona o sistema de duplicidade"):
    st.markdown("""
    ### 🛡️ Mecanismo de Prevenção de Duplicidade
    
    1. **Session ID Único**: Cada usuário recebe um ID de sessão único ao acessar
    2. **Cookie Hash**: Um hash criptográfico é armazenado no navegador
    3. **Validação no Banco**: O session_id é verificado antes de permitir resposta
    4. **Constraint UNIQUE**: O banco de dados impede duplicatas no nível de dados
    5. **Auditoria**: Tentativas bloqueadas são registradas
    
    ### 🔒 Privacidade mantida
    - Nenhum dado pessoal é armazenado
    - O session_id é aleatório e não rastreável
    - O cookie expira automaticamente após 24 horas
    """)

# Executar o app de teste
if __name__ == "__main__":
    # O Streamlit já cuida da execução
    pass