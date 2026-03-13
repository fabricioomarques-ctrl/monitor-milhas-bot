import time
from datetime import datetime

import requests

from config import (
    TELEGRAM_TOKEN,
    CHAT_ID,
    CANAL_ID,
    INTERVALO_RADAR,
    POLL_INTERVAL,
    LIMITE_COMANDO,
    SCORE_MINIMO_ALERTA,
    MAX_ALERTAS_CONSOLIDADOS,
)
from engine.radar import executar_radar
from engine.scoring import chave_duplicacao
from storage.deduplicador import (
    carregar_alertas_enviados,
    salvar_alertas_enviados,
)


LAST_RADAR_RUN = None
LAST_RESULTS_COUNT = 0
LAST_SENT_COUNT = 0
LAST_ERROR = ""
LAST_UPDATE_ID = None
LAST_SOURCE_SUMMARY = {}


def telegram_api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"


def destinos_alerta() -> list[str]:
    destinos = []

    if CHAT_ID:
        destinos.append(CHAT_ID)

    if CANAL_ID and CANAL_ID not in destinos:
        destinos.append(CANAL_ID)

    return destinos


def enviar_telegram(mensagem: str, chat_id: str | None = None) -> bool:
    if not TELEGRAM_TOKEN:
        print("Telegram não configurado")
        return False

    destinos = [chat_id] if chat_id else destinos_alerta()

    sucesso = False

    for destino in destinos:
        if not destino:
            continue

        try:
            r = requests.post(
                telegram_api_url("sendMessage"),
                json={"chat_id": destino, "text": mensagem},
                timeout=20
            )

            if r.status_code == 200:
                sucesso = True
            else:
                print("Erro Telegram status:", r.status_code, r.text)

        except Exception as e:
            print("Erro Telegram:", e)

    return sucesso


def obter_updates(offset: int | None = None) -> list[dict]:
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


def montar_alerta_consolidado(resultados: list[dict]) -> str:
    if not resultados:
        return ""

    msg = "🚨 RADAR DE MILHAS PRO\n\n"
    msg += f"{len(resultados)} oportunidade(s) relevante(s) detectada(s)\n\n"

    for i, r in enumerate(resultados[:MAX_ALERTAS_CONSOLIDADOS], 1):
        msg += (
            f"{i}️⃣ {r.get('titulo', '')}\n"
            f"📝 {r.get('detalhe', '')}\n"
            f"📊 Score: {r.get('score', 0)}/10\n"
            f"{r.get('classificacao', '')}\n"
            f"{r.get('link', '')}\n\n"
        )

    return msg.strip()


def texto_menu() -> str:
    return (
        "✈️ Radar de Milhas PRO v3\n\n"
        "/menu\n"
        "/promocoes\n"
        "/transferencias\n"
        "/passagens\n"
        "/ranking\n"
        "/status\n"
        "/teste"
    )


def texto_status() -> str:
    ultima_execucao = LAST_RADAR_RUN or "ainda não executado"
    erro = LAST_ERROR or "nenhum"

    return (
        "🟢 Radar online\n\n"
        f"⏱ Intervalo do radar: {INTERVALO_RADAR} segundos\n"
        f"📥 Últimos resultados encontrados: {LAST_RESULTS_COUNT}\n"
        f"📤 Últimos alertas enviados: {LAST_SENT_COUNT}\n"
        f"🕒 Última execução: {ultima_execucao}\n"
        f"⚠️ Último erro: {erro}"
    )


def texto_sem_resultado(titulo: str) -> str:
    return f"{titulo}\n\nNenhuma oportunidade detectada no momento."


def formatar_lista_resultados(titulo: str, resultados: list[dict], limite: int = LIMITE_COMANDO) -> str:
    if not resultados:
        return texto_sem_resultado(titulo)

    msg = f"{titulo}\n\n"

    for i, resultado in enumerate(resultados[:limite], 1):
        msg += (
            f"{i}️⃣ {resultado.get('titulo', '')}\n"
            f"📍 Fonte: {resultado.get('fonte', '')}\n"
            f"📝 {resultado.get('detalhe', '')}\n"
            f"📊 Score: {resultado.get('score', 0)}/10\n"
            f"✅ Confirmada em {resultado.get('confirmado_fontes', 1)} fonte(s)\n"
            f"{resultado.get('classificacao', '🟢 PROMOÇÃO BOA')}\n"
            f"{resultado.get('link', '')}\n\n"
        )

    return msg.strip()


def filtrar_por_tipo(resultados: list[dict], tipos: list[str]) -> list[dict]:
    return [r for r in resultados if r.get("tipo") in tipos]


def executar_teste_manual(chat_id: str) -> None:
    try:
        resultados = executar_radar()
        enviar_telegram(
            formatar_lista_resultados("🧪 Teste do radar", resultados),
            chat_id=chat_id
        )
    except Exception as e:
        enviar_telegram(f"❌ Erro no /teste: {e}", chat_id=chat_id)


def processar_comando(texto: str, chat_id: str) -> None:
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


def processar_updates() -> None:
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


def executar_ciclo_radar(alertas_enviados: set) -> None:
    global LAST_RADAR_RUN, LAST_RESULTS_COUNT, LAST_SENT_COUNT, LAST_ERROR

    enviados_nesta_execucao = 0

    try:
        resultados = executar_radar()
        LAST_RESULTS_COUNT = len(resultados)

        fortes = []

        for resultado in resultados:
            if resultado.get("score", 0) < SCORE_MINIMO_ALERTA:
                continue

            chave = chave_duplicacao(resultado)

            if chave in alertas_enviados:
                continue

            fortes.append(resultado)
            alertas_enviados.add(chave)

        if fortes:
            mensagem = montar_alerta_consolidado(fortes)

            if mensagem and enviar_telegram(mensagem):
                enviados_nesta_execucao = len(fortes)

        salvar_alertas_enviados(alertas_enviados)

        LAST_SENT_COUNT = enviados_nesta_execucao
        LAST_ERROR = ""
        LAST_RADAR_RUN = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"Resultados encontrados: {LAST_RESULTS_COUNT}")
        print(f"Alertas enviados: {LAST_SENT_COUNT}")

    except Exception as e:
        LAST_ERROR = str(e)
        LAST_RADAR_RUN = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("Erro loop:", e)


def main() -> None:
    print("Radar de Milhas PRO v3 iniciado")

    if not TELEGRAM_TOKEN:
        print("TELEGRAM_TOKEN não configurado")

    alertas_enviados = carregar_alertas_enviados()
    proxima_execucao_radar = 0

    while True:
        processar_updates()

        agora = time.time()

        if agora >= proxima_execucao_radar:
            executar_ciclo_radar(alertas_enviados)
            proxima_execucao_radar = agora + INTERVALO_RADAR

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
