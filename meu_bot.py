import sqlite3
import threading
import time
import requests
import streamlit as st

# --- CONFIGURAÇÕES DO TELEGRAM (Bot Principal) ---
TOKEN_TELEGRAM = "8532710383:AAHhhsE2zuKf0bLqiy38pfY7kSS2R2FQ1yw"

MOEDAS_PADRAO = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "MONUSDT"]
precos_anteriores = {}

# --- 1. CONFIGURAÇÃO DA BASE DE DADOS (SQLite) ---
def inicializar_bd():
    conexao = sqlite3.connect("historico_alertas.db", check_same_thread=False)
    cursor = conexao.cursor()
    
    # Tabela para o histórico de alertas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            moeda TEXT,
            mensagem TEXT
        )
    """)
    
    # Tabela nova para gerir os subscritores dinamicamente (SaaS)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscritores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT UNIQUE,
            nome TEXT
        )
    """)
    
    conexao.commit()
    return conexao, cursor

conexao_bd, cursor_bd = inicializar_bd()

# --- 2. SISTEMA DE ALERTAS MULTI-SUBSCRIÇÃO VIA TELEGRAM ---
def enviar_alerta_telegram(mensagem, moeda):
    try:
        data_atual = time.strftime("%Y-%m-%d %H:%M:%S")
        cursor_bd.execute(
            "INSERT INTO alertas (data, moeda, mensagem) VALUES (?, ?, ?)",
            (data_atual, moeda, mensagem),
        )
        conexao_bd.commit()

        # Buscar todos os subscritores registados na base de dados
        cursor_bd.execute("SELECT chat_id FROM subscritores")
        subscritores = cursor_bd.fetchall()

        if not subscritores:
            print("⚠️ Nenhum subscritor registado para receber alertas.")
            return

        # Enviar o alerta para cada Chat ID presente na base de dados
        url_api = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
        
        for sub in subscritores:
            chat_id = sub[0]
            payload = {
                "chat_id": chat_id,
                "text": mensagem,
                "parse_mode": "Markdown"
            }
            
            resposta = requests.post(url_api, json=payload)
            if resposta.status_code == 200:
                print(f"📲 Alerta enviado com sucesso para o Chat ID: {chat_id}")
            else:
                print(f"Erro ao enviar para o Chat ID {chat_id}: {resposta.text}")
            
    except Exception as e:
        print(f"Erro no sistema de alertas: {e}")

# --- 3. MOTOR DE MONITORIZAÇÃO (Em Segundo Plano) ---
def executar_bot(moedas, limiar_perc, preco_alvo_custom, direcao_filtro):
    global precos_anteriores
    print("--- Bot Avançado Iniciado (SaaS Mode) ---")

    while True:
        for simbolo in moedas:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={simbolo}"
            try:
                resposta = requests.get(url)
                dados = resposta.json()

                if "price" in dados:
                    preco_atual = float(dados["price"])

                    # Verificação de Preço Alvo Exato para o Bitcoin (opcional)
                    if (
                        preco_alvo_custom
                        and simbolo == "BTCUSDT"
                        and preco_atual >= preco_alvo_custom
                    ):
                        texto_alerta = f"🎯 *ALERTA DE PREÇO-ALVO BTC*: Atingiu `${preco_atual:,.2f}`!"
                        enviar_alerta_telegram(texto_alerta, simbolo)

                    # Verificação de Variação Percentual
                    if simbolo in precos_anteriores:
                        preco_ant = precos_anteriores[simbolo]
                        variacao = ((preco_atual - preco_ant) / preco_ant) * 100

                        print(f"[{simbolo}] Preço: ${preco_atual:,.2f} | Variação: {variacao:+.3f}%")

                        if abs(variacao) >= limiar_perc:
                            disparar = False
                            if direcao_filtro == "Apenas Subidas" and variacao > 0:
                                disparar = True
                            elif direcao_filtro == "Apenas Quedas" and variacao < 0:
                                disparar = True
                            elif direcao_filtro == "Ambos (Subidas e Quedas)":
                                disparar = True

                            if disparar:
                                if variacao > 0:
                                    texto_alerta = f"🚀 *ALERTA {simbolo}*: Subiu para `${preco_atual:,.2f}` (`{variacao:+.3f}%`)!"
                                else:
                                    texto_alerta = f"⚠️ *ALERTA {simbolo}*: Caiu para `${preco_atual:,.2f}` (`{variacao:+.3f}%`)!"

                                enviar_alerta_telegram(texto_alerta, simbolo)
                    else:
                        print(f"[{simbolo}] Referência inicial: ${preco_atual:,.2f}")

                    precos_anteriores[simbolo] = preco_atual

            except Exception as e:
                print(f"Erro ao consultar {simbolo}: {e}")

            time.sleep(1)
        time.sleep(10)

# --- 4. INTERFACE GRÁFICA (Streamlit) ---
def main():
    st.title("⚡ Crypto Bot Pro - Painel SaaS")
    st.write("Plataforma automatizada de sinais e alertas de criptomoedas em tempo real.")

    # --- SECÇÃO DE GESTÃO DE SUBSCRITORES NO SIDEBAR ---
    st.sidebar.header("👤 Gestão de Subscritores")
    novo_nome = st.sidebar.text_input("Nome do Utilizador")
    novo_chat_id = st.sidebar.text_input("Chat ID do Telegram")

    if st.sidebar.button("➕ Registar Subscritor"):
        if novo_chat_id and novo_nome:
            try:
                cursor_bd.execute(
                    "INSERT INTO subscritores (chat_id, nome) VALUES (?, ?)",
                    (novo_chat_id, novo_nome),
                )
                conexao_bd.commit()
                st.sidebar.success(f"Utilizador {novo_nome} registado com sucesso!")
            except sqlite3.IntegrityError:
                st.sidebar.warning("Este Chat ID já se encontra registado.")
        else:
            st.sidebar.error("Preenche o nome e o Chat ID.")

    st.sidebar.divider()
    st.sidebar.header("⚙️ Definições do Bot")

    moedas_selecionadas = st.sidebar.multiselect(
        "Moedas a monitorizar",
        ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "MONUSDT", "XRPUSDT", "ADAUSDT"],
        default=MOEDAS_PADRAO,
    )

    limiar = st.sidebar.slider("Limiar de Variação (%)", 0.01, 1.0, 0.1, step=0.01)

    direcao = st.sidebar.selectbox(
        "Direção dos Alertas",
        ["Ambos (Subidas e Quedas)", "Apenas Subidas", "Apenas Quedas"],
    )

    preco_btc_alvo = st.sidebar.number_input(
        "Definir Preço-Alvo Fixo (BTC - Opcional)", value=0.0, step=100.0
    )

    if "bot_iniciado" not in st.session_state:
        if st.sidebar.button("🚀 Iniciar Bot"):
            t = threading.Thread(
                target=executar_bot,
                args=(moedas_selecionadas, limiar, preco_btc_alvo, direcao),
                daemon=True,
            )
            t.start()
            st.session_state["bot_iniciado"] = True
            st.sidebar.success("Bot em execução para todos os subscritores!")

    # --- CORPO PRINCIPAL DA APP ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👥 Lista de Subscritores Ativos")
        cursor_bd.execute("SELECT nome, chat_id FROM subscritores")
        subs = cursor_bd.fetchall()
        if subs:
            for s in subs:
                st.write(f"- **{s[0]}** (ID: `{s[1]}`)")
        else:
            st.info("Ainda não há subscritores registados.")

    with col2:
        st.subheader("📊 Histórico de Alertas")
        if st.button("🔄 Atualizar Histórico"):
            pass
            
    cursor_bd.execute("SELECT data, moeda, mensagem FROM alertas ORDER BY id DESC LIMIT 10")
    historico = cursor_bd.fetchall()
    if historico:
        for linha in historico:
            st.write(f"**[{linha[0]}] ({linha[1]}):** {linha[2]}")
    else:
        st.info("Ainda não existem alertas disparados.")

if __name__ == "__main__":
    main()