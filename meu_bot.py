import streamlit as st
import requests
import time
from datetime import datetime

# ================= CONFIGURAÇÕES DO TELEGRAM =================
TOKEN = "7550457419:AAFw9o7k9f39nS6c6_v6R6Z53h1-v2j2K9E"  # Token recuperado do teu histórico / sessão
LINK_GRUPO = "https://t.me/+aEbBvr1wOCxhZDI0"

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Crypto Bot Pro - Painel SaaS",
    page_icon="⚡",
    layout="wide"
)

# Inicializar bases de dados na sessão se não existirem
if 'subscritores' not in st.session_state:
    st.session_state.subscritores = []

if 'historico_alertas' not in st.session_state:
    st.session_state.historico_alertas = []

if 'bot_a_correr' not in st.session_state:
    st.session_state.bot_a_correr = False


def enviar_mensagem_telegram(chat_id, texto):
    """Envia uma mensagem de texto para um chat específico do Telegram."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Erro ao enviar mensagem Telegram: {e}")


def enviar_convite_grupo(chat_id, nome):
    """Envia o link de convite do grupo por mensagem privada ao novo subscritor."""
    mensagem = (
        f"⚡ *Olá {nome}!* O teu registo no *Crypto Bot Pro* foi efetuado com sucesso.\n\n"
        f"🔗 Podes aceder ao nosso grupo oficial através do link abaixo:\n"
        f"{LINK_GRUPO}"
    )
    enviar_mensagem_telegram(chat_id, mensagem)


# ================= MENU LATERAL =================
st.sidebar.title("⚡ Gestão de Subscritores")

nome_sub = st.sidebar.text_input("Nome do Utilizador")
chat_id_sub = st.sidebar.text_input("Chat ID do Telegram")

if st.sidebar.button("➕ Registar Subscritor"):
    if nome_sub and chat_id_sub:
        existe = any(s['chat_id'] == chat_id_sub for s in st.session_state.subscritores)
        if not existe:
            st.session_state.subscritores.append({"nome": nome_sub, "chat_id": chat_id_sub})
            st.sidebar.success(f"Subscritor {nome_sub} registado com sucesso!")
            
            # Enviar mensagem de boas-vindas e link do grupo automaticamente
            enviar_convite_grupo(chat_id_sub, nome_sub)
        else:
            st.sidebar.warning("Este Chat ID já se encontra registado.")
    else:
        st.sidebar.error("Preenche o nome e o Chat ID.")

st.sidebar.markdown("---")
st.sidebar.title("⚙️ Definições do Bot")

moedas_selecionadas = st.sidebar.multiselect(
    "Moedas a monitorizar",
    ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"],
    default=["BTCUSDT", "ETHUSDT", "BNBUSDT"]
)

limiar_variacao = st.sidebar.slider("Limiar de Variação (%)", 0.01, 5.0, 0.10, 0.01)

direcao = st.sidebar.selectbox(
    "Direção dos Alertas",
    ["Ambos (Subidas e Quedas)", "Apenas Subidas", "Apenas Quedas"]
)

st.sidebar.markdown("---")
col_start, col_stop = st.sidebar.columns(2)
with col_start:
    if st.button("🚀 Iniciar Bot"):
        st.session_state.bot_a_correr = True
with col_stop:
    if st.button("⏹️ Parar Bot"):
        st.session_state.bot_a_correr = False

# ================= CORPO PRINCIPAL =================
st.title("⚡ Crypto Bot Pro - Painel SaaS")
st.markdown("Plataforma automatizada de sinais e alertas de criptomoedas em tempo real.")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 👥 Lista de Subscritores Ativos")
    if st.session_state.subscritores:
        for sub in st.session_state.subscritores:
            st.markdown(f"- **{sub['nome']}** (ID: `{sub['chat_id']}`)")
    else:
        st.info("Ainda não há subscritores registados.")

with col2:
    st.markdown("### 📊 Histórico de Alertas")
    if st.button("🔄 Atualizar Histórico"):
        st.rerun()
    
    if st.session_state.historico_alertas:
        for alerta in reversed(st.session_state.historico_alertas[-10:]):
            st.text(alerta)
    else:
        st.info("Ainda não existem alertas disparados.")

# ================= MOTOR DE MONITORIZAÇÃO =================
if st.session_state.bot_a_correr:
    if not moedas_selecionadas:
        st.warning("Seleciona pelo menos uma moeda para monitorizar.")
    elif not st.session_state.subscritores:
        st.warning("Adiciona pelo menos um subscritor para enviar os sinais.")
    else:
        status_placeholder = st.empty()
        status_placeholder.info("🟢 Bot a monitorizar o mercado ativamente em segundo plano...")
        
        precos_anteriores = {}
        
        for _ in range(50):
            if not st.session_state.bot_a_correr:
                break
                
            for moeda in moedas_selecionadas:
                try:
                    url_binance = f"https://api.binance.com/api/v3/ticker/price?symbol={moeda}"
                    resposta = requests.get(url_binance, timeout=3).json()
                    
                    if 'price' not in resposta:
                        continue
                        
                    preco_atual = float(resposta['price'])
                    
                    if moeda not in precos_anteriores:
                        precos_anteriores[moeda] = preco_atual
                        continue
                    
                    preco_ant = precos_anteriores[moeda]
                    variacao = ((preco_atual - preco_ant) / preco_ant) * 100
                    
                    disparar = False
                    if abs(variacao) >= limiar_variacao:
                        if direcao == "Ambos (Subidas e Quedas)":
                            disparar = True
                        elif direcao == "Apenas Subidas" and variacao > 0:
                            disparar = True
                        elif direcao == "Apenas Quedas" and variacao < 0:
                            disparar = True
                    
                    if disparar:
                        emoji = "🚀" if variacao > 0 else "🔻"
                        tipo_mov = "SUBIDA" if variacao > 0 else "QUEDA"
                        
                        mensagem_alerta = (
                            f"{emoji} *ALERTA DE CRIPTO - {moeda}* {emoji}\n\n"
                            f"📈 Movimento: *{tipo_mov}*\n"
                            f"💵 Preço Atual: *${preco_atual:,.2f}*\n"
                            f"📊 Variação: *{variacao:+.2f}%*\n"
                            f"⏰ Hora: {datetime.now().strftime('%H:%M:%S')}"
                        )
                        
                        for sub in st.session_state.subscritores:
                            enviar_mensagem_telegram(sub['chat_id'], mensagem_alerta)
                        
                        registo_historico = f"[{datetime.now().strftime('%H:%M:%S')}] {moeda} -> {variacao:+.2f}% (Preço: ${preco_atual:,.2f})"
                        st.session_state.historico_alertas.append(registo_historico)
                        
                        precos_anteriores[moeda] = preco_atual
                        
                except Exception as e:
                    print(f"Erro ao consultar Binance para {moeda}: {e}")
            
            time.sleep(5)
        
        st.rerun()
