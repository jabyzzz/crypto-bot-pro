import sqlite3
import threading
import time
import pyautogui
import pywhatkit as pwk
import requests
import streamlit as st

# --- CONFIGURAÇÕES GLOBAIS ---
TELEFONE_DESTINO = "+351932387723"
MOEDAS_PADRAO = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
precos_anteriores = {}

# --- 1. CONFIGURAÇÃO DA BASE DE DADOS (SQLite) ---
def inicializar_bd():
  conexao = sqlite3.connect("historico_alertas.db", check_same_thread=False)
  cursor = conexao.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            moeda TEXT,
            mensagem TEXT
        )
    """)
  conexao.commit()
  return conexao, cursor


conexao_bd, cursor_bd = inicializar_bd()


# --- 2. SISTEMA DE WHATSAPP ---
def enviar_alerta_whatsapp(mensagem, moeda):
  try:
    # Regista o alerta na Base de Dados
    data_atual = time.strftime("%Y-%m-%d %H:%M:%S")
    cursor_bd.execute(
        "INSERT INTO alertas (data, moeda, mensagem) VALUES (?, ?, ?)",
        (data_atual, moeda, mensagem),
    )
    conexao_bd.commit()

    # Envio automático via WhatsApp
    pwk.sendwhatmsg_instantly(
        phone_no=TELEFONE_DESTINO, message=mensagem, wait_time=12, tab_close=False
    )
    time.sleep(3)
    pyautogui.press("enter")
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(3)
    pyautogui.hotkey("ctrl", "w")
    print(f"📲 Alerta enviado e guardado para {moeda}!")
  except Exception as e:
    print(f"Erro ao enviar WhatsApp: {e}")


# --- 3. MOTOR DE MONITORIZAÇÃO ---
def executar_bot(moedas, limiar_perc, preco_alvo_custom, direcao_filtro):
  global precos_anteriores
  print("--- Bot Avançado Iniciado em Segundo Plano ---")

  while True:
    for simbolo in moedas:
      url = f"https://api.binance.com/api/v3/ticker/price?symbol={simbolo}"
      try:
        resposta = requests.get(url)
        dados = resposta.json()

        if "price" in dados:
          preco_atual = float(dados["price"])

          # Verificação de Preço Alvo Exato (se definido)
          if (
              preco_alvo_custom
              and simbolo == "BTCUSDT"
              and preco_atual >= preco_alvo_custom
          ):
            texto_alerta = (
                f"🎯 ALERTA DE PREÇO-ALVO BTC: Atingiu ${preco_atual:,.2f}!"
            )
            enviar_alerta_whatsapp(texto_alerta, simbolo)

          # Verificação de Variação Percentual
          if simbolo in precos_anteriores:
            preco_ant = precos_anteriores[simbolo]
            variacao = ((preco_atual - preco_ant) / preco_ant) * 100

            print(
                f"[{simbolo}] Preço: ${preco_atual:,.2f} | Variação:"
                f" {variacao:+.3f}%"
            )

            if abs(variacao) >= limiar_perc:
              # Filtro de direção (Apenas subidas, apenas quedas ou ambos)
              disparar = False
              if direcao_filtro == "Apenas Subidas" and variacao > 0:
                disparar = True
              elif direcao_filtro == "Apenas Quedas" and variacao < 0:
                disparar = True
              elif direcao_filtro == "Ambos (Subidas e Quedas)":
                disparar = True

              if disparar:
                if variacao > 0:
                  texto_alerta = (
                      f"🚀 ALERTA {simbolo}: Subiu para ${preco_atual:,.2f}"
                      f" ({variacao:+.3f}%)!"
                  )
                else:
                  texto_alerta = (
                      f"⚠️ ALERTA {simbolo}: Caiu para ${preco_atual:,.2f}"
                      f" ({variacao:+.3f}%)!"
                  )

                enviar_alerta_whatsapp(texto_alerta, simbolo)
          else:
            print(f"[{simbolo}] Referência inicial: ${preco_atual:,.2f}")

          precos_anteriores[simbolo] = preco_atual

      except Exception as e:
        print(f"Erro ao consultar {simbolo}: {e}")

      time.sleep(1)
    time.sleep(10)


# --- 4. INTERFACE GRÁFICA (Streamlit) ---
def main():
  st.title("⚡ Crypto Bot Pro - Painel de Controlo")
  st.write(
      "Gerencia os teus alertas automáticos de criptomoedas e monitoriza o"
      " histórico."
  )

  # Sidebar de Configurações
  st.sidebar.header("Definições do Bot")
  moedas_selecionadas = st.sidebar.multiselect(
      "Moedas a monitorizar",
      ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"],
      default=MOEDAS_PADRAO,
  )

  limiar = st.sidebar.slider(
      "Limiar de Variação (%)", 0.01, 1.0, 0.1, step=0.01
  )

  direcao = st.sidebar.selectbox(
      "Direção dos Alertas",
      ["Ambos (Subidas e Quedas)", "Apenas Subidas", "Apenas Quedas"],
  )

  preco_btc_alvo = st.sidebar.number_input(
      "Definir Preço-Alvo Fixo (BTC - Opcional)", value=0.0, step=100.0
  )

  # Iniciar o bot numa thread separada para não bloquear a página web
  if "bot_iniciado" not in st.session_state:
    if st.sidebar.button("🚀 Iniciar Bot"):
      t = threading.Thread(
          target=executar_bot,
          args=(
              moedas_selecionadas,
              limiar,
              preco_btc_alvo,
              direcao,
          ),
          daemon=True,
      )
      t.start()
      st.session_state["bot_iniciado"] = True
      st.sidebar.success("Bot a correr em segundo plano!")

  # Secção de Histórico guardado na Base de Dados
  st.divider()
  st.subheader("📊 Histórico de Alertas Disparados")

  if st.button("🔄 Atualizar Histórico"):
    cursor_bd.execute(
        "SELECT data, moeda, mensagem FROM alertas ORDER BY id DESC"
    )
    historico = cursor_bd.fetchall()
    if historico:
      for linha in historico:
        st.write(f"**[{linha[0]}] ({linha[1]}):** {linha[2]}")
    else:
      st.info("Ainda não existem alertas registados.")


if __name__ == "__main__":
  main()
