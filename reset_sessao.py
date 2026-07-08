# reset_sessao.py
import streamlit as st

st.set_page_config(
    page_title="Resetar Sessão",
    page_icon="🔄"
)

st.title("🔄 Resetar Sessão")

if st.button("Resetar Sessão"):
    # Limpar todas as chaves da sessão
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    st.success("✅ Sessão resetada com sucesso!")
    st.info("Clique no botão abaixo para recarregar e acessar a pesquisa")
    
    if st.button("📊 Ir para Pesquisa"):
        st.switch_page("app.py")

# Ou ir direto para a pesquisa
st.markdown("---")
st.markdown("### Ou acesse diretamente:")
if st.button("🚀 Acessar Pesquisa"):
    st.switch_page("app.py")