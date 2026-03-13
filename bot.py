import time
from datetime import datetime

import requests

from config import TELEGRAM_TOKEN, CHAT_ID, INTERVALO, POLL_INTERVAL, LIMITE_COMANDO
from engine.radar import executar_radar
from storage.estado import (
    carregar_promocoes_enviadas,
    salvar_promocoes_enviadas
)


LAST_RADAR_RUN = None
LAST_RESULTS_COUNT = 0
LAST_SENT_COUNT = 0
LAST_ERROR = ""
LAST_UPDATE_ID = None


def telegram_api_url(method):
    return f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"


def enviar_telegram(mensagem, chat_id=None):
    destino = chat_id or CHAT_ID

    if not TELEGRAM_TOKEN or not destino:
        print("Telegram não configurado")
        return False

    try:
        r = requests.post(
            telegram_api_url("sendMessage"),
            json={
                "chat_id": destino,
                "text": mensagem
            },
            timeout=20
        )

        if r.status_code == 200:
            print("Mensagem enviada ao Telegram com sucesso")
            return True

        print("Erro Telegram status:", r.status_code, r.text)
        return False

    except Exception as e:
        print("Erro Telegram:", e)
        return False


def obter_updates(offset=None):
    if not TELEGRAM_TOKEN:
        return []

    params = {
        "timeout": 0,
        "allowed_updates": ["message"]
    }

    if offset is not None:
        params["offset"] = offset

    try:
        r = requests.get(
            telegram_api_url("getUpdates"),
            params=params,
            timeout=20
        )

        if r.status_code != 200:
            print("Erro getUpdates:", r.status_code, r.text)
            return []

        data = r.json()

        if not data.get("ok"):
            return []

        return data.get("result", [])

    except Exception as e:
        print("Erro ao obter updates:", e)
        return []


def chave_resultado(resultado):
    return f"{resultado.get('tipo')}|{resultado.get('link')}"


def montar_alerta(resultado):
    tipo = resultado.get("tipo", "")
    titulo = resultado.get("titulo", "")
    detalhe = resultado.get("detalhe", "")
    link = resultado.get("link", "")
    fonte = resultado.get("fonte", "")
    score = resultado.get("score", 0)
    classificacao = resultado.get("classificacao", "⚪ OPORTUNIDADE PADRÃO")

    prefixos = {
        "transferencia_bonificada": "🔁 TRANSFERÊNCIA BONIFICADA",
        "milheiro_barato": "💰 MILHEIRO BARATO",
        "passagem_barata": "✈️ PASSAGEM BARATA",
    }

    prefixo = prefixos.get(tipo, "📡 OPORTUNIDADE DETECTADA")

    return (
        f"{prefixo}\n\n"
        f"📌 {titulo}\n"
        f"📍 Fonte: {fonte}\n"
        f"📝 {detalhe}\n"
        f"📊 Score: {score}\n"
        f"{classificacao}\n\n"
        f"{link}"
    )


def texto_menu():
    return (
        "✈️ Radar de Milhas PRO\n\n"
        "/menu\n"
        "/promocoes\n"
        "/transferencias\n"
        "/passagens\n"
        "/ranking\n"
        "/status\n"
        "/teste"
    )


def texto_status():
    ultima_execucao = LAST_RADAR_RUN or "ainda não executado"
    erro = LAST_ERROR or "nenhum"

    return (
        "🟢 Radar online\n\n"
        f"⏱ Intervalo do radar: {INTERVALO} segundos\n"
        f"📥 Últimos resultados encontrados: {LAST_RESULTS_COUNT}\n"
        f"📤 Últimos alertas enviados: {LAST_SENT_COUNT}\n"
        f"🕒 Última execução: {ultima_execucao}\n"
        f"⚠️ Último erro: {erro}"
    )


def texto_sem_resultado(titulo):
    return f"{titulo}\n\nNenhuma oportunidade detectada no momento."


def formatar_lista_resultados(titulo, resultados, limite=LIMITE_COMANDO):
    if not resultados:
        return texto_sem_resultado(titulo)

    msg = f"{titulo}\n\n"

    for i, resultado in enumerate(resultados[:limite], 1):
        msg += (
            f"{i}️⃣ {resultado.get('titulo', '')}\n"
            f"📍 Fonte: {resultado.get('fonte', '')}\n"
            f"📝 {resultado.get('detalhe', '')}\n"
            f"📊 Score: {resultado.get('score', 0)}\n"
            f"{resultado.get('classificacao', '⚪ OPORTUNIDADE PADRÃO')}\n"
            f"{resultado.get('link', '')}\n\n"
        )

    return msg.strip()


def filtrar_por_tipo(resultados, tipos):
    return [r for r in resultados if r.get("tipo") in tipos]


def executar_teste_manual(chat_id):
    try:
        resultados = executar_radar()

        enviar_telegram(
            formatar_lista_resultados(
                "🧪 Teste do radar",
                resultados
            ),
            chat_id=chat_id
        )

    except Exception as e:
        enviar_telegram(
            f"❌ Erro no /teste: {e}",
            chat_id=chat_id
        )


def processar_comando(texto, chat_id):
    comando = str(texto or "").strip().lower()

    if comando == "/start":
        enviar_telegram(texto_menu(), chat_id=chat_id)
        return

    if comando == "/menu":
        enviar_telegram(
            "📡 MENU\n\n"
            "/promocoes\n"
            "/transferencias\n"
            "/passagens\n"
            "/ranking\n"
            "/status\n"
            "/teste",
            chat_id=chat_id
        )
        return

    if comando == "/status":
        enviar_telegram(texto_status(), chat_id=chat_id)
        return

    if comando == "/teste":
        executar_teste_manual(chat_id)
        return

    if comando == "/promocoes":
        try:
            resultados = executar_radar()
            bonus = filtrar_por_tipo(resultados, ["transferencia_bonificada"])
            enviar_telegram(
                formatar_lista_resultados("🔥 Promoções detectadas", bonus),
                chat_id=chat_id
            )
        except Exception as e:
            enviar_telegram(f"❌ Erro em /promocoes: {e}", chat_id=chat_id)
        return

    if comando == "/transferencias":
        try:
            resultados = executar_radar()
            transf = filtrar_por_tipo(resultados, ["transferencia_bonificada"])
            enviar_telegram(
                formatar_lista_resultados("🔁 Transferências detectadas", transf),
                chat_id=chat_id
            )
        except Exception as e:
            enviar_telegram(f"❌ Erro em /transferencias: {e}", chat_id=chat_id)
        return

    if comando == "/passagens":
        try:
            resultados = executar_radar()
            passagens = filtrar_por_tipo(resultados, ["passagem_barata"])
            enviar_telegram(
                formatar_lista_resultados("✈️ Passagens detectadas", passagens),
                chat_id=chat_id
            )
        except Exception as e:
            enviar_telegram(f"❌ Erro em /passagens: {e}", chat_id=chat_id)
        return

    if comando == "/ranking":
        try:
            resultados = executar_radar()
            enviar_telegram(
                formatar_lista_resultados("🏆 Ranking atual do radar", resultados),
                chat_id=chat_id
            )
        except Exception as e:
            enviar_telegram(f"❌ Erro em /ranking: {e}", chat_id=chat_id)
        return


def processar_updates():
    global LAST_UPDATE_ID

    updates = obter_updates(
        offset=(LAST_UPDATE_ID + 1) if LAST_UPDATE_ID is not None else None
    )

    for update in updates:
        LAST_UPDATE_ID = update.get("update_id", LAST_UPDATE_ID)

        message = update.get("message", {})
        text = message.get("text", "")
        chat = message.get("chat", {})
        chat_id = chat.get("id")

        if not text or not chat_id:
            continue

        if text.startswith("/"):
            processar_comando(text, chat_id)


def executar_ciclo_radar(enviados):
    global LAST_RADAR_RUN, LAST_RESULTS_COUNT, LAST_SENT_COUNT, LAST_ERROR

    enviados_nesta_execucao = 0

    try:
        resultados = executar_radar()
        LAST_RESULTS_COUNT = len(resultados)

        for resultado in resultados:
            chave = chave_resultado(resultado)

            if chave in enviados:
                print("Resultado já enviado, pulando:", chave)
                continue

            mensagem = montar_alerta(resultado)

            if enviar_telegram(mensagem):
                enviados.add(chave)
                enviados_nesta_execucao += 1

        salvar_promocoes_enviadas(enviados)

        LAST_SENT_COUNT = enviados_nesta_execucao
        LAST_ERROR = ""
        LAST_RADAR_RUN = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"Resultados encontrados: {LAST_RESULTS_COUNT}")
        print(f"Alertas enviados: {LAST_SENT_COUNT}")

    except Exception as e:
        LAST_ERROR = str(e)
        LAST_RADAR_RUN = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("Erro loop:", e)


def main():
    print("Radar iniciado")

    if not TELEGRAM_TOKEN:
        print("TELEGRAM_TOKEN não configurado")

    enviados = carregar_promocoes_enviadas()
    proxima_execucao_radar = 0

    while True:
        processar_updates()

        agora = time.time()

        if agora >= proxima_execucao_radar:
            executar_ciclo_radar(enviados)
            proxima_execucao_radar = agora + INTERVALO

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
