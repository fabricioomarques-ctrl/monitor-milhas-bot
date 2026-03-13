import time
import requests

from config import TELEGRAM_TOKEN, CHAT_ID, INTERVALO
from engine.radar import executar_radar
from storage.estado import (
    carregar_promocoes_enviadas,
    salvar_promocoes_enviadas
)


def enviar_telegram(mensagem):

    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Telegram não configurado")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:
        requests.post(
            url,
            json={
                "chat_id": CHAT_ID,
                "text": mensagem
            },
            timeout=20
        )
        print("Mensagem enviada ao Telegram com sucesso")

    except Exception as e:
        print("Erro Telegram:", e)


def montar_mensagem(resultado):

    tipo = resultado.get("tipo", "")
    titulo = resultado.get("titulo", "")
    detalhe = resultado.get("detalhe", "")
    link = resultado.get("link", "")
    fonte = resultado.get("fonte", "")

    prefixos = {
        "bonus_alto": "🔥 BÔNUS ALTO DETECTADO",
        "transferencia_bonificada": "🔁 TRANSFERÊNCIA BONIFICADA",
        "milheiro_barato": "💰 MILHEIRO BARATO",
    }

    prefixo = prefixos.get(
        tipo,
        "📡 OPORTUNIDADE DETECTADA"
    )

    return (
        f"{prefixo}\n\n"
        f"📌 {titulo}\n"
        f"📍 Fonte: {fonte}\n"
        f"📝 {detalhe}\n\n"
        f"{link}"
    )


def chave_resultado(resultado):

    return f"{resultado.get('tipo')}|{resultado.get('link')}"


def main():

    print("Radar iniciado")

    enviados = carregar_promocoes_enviadas()

    while True:

        try:
            resultados = executar_radar()

            print(f"Resultados encontrados: {len(resultados)}")

            for resultado in resultados:

                chave = chave_resultado(resultado)

                if chave in enviados:
                    print("Resultado já enviado, pulando:", chave)
                    continue

                mensagem = montar_mensagem(resultado)

                enviar_telegram(mensagem)

                enviados.add(chave)

            salvar_promocoes_enviadas(enviados)

        except Exception as e:
            print("Erro loop:", e)

        time.sleep(INTERVALO)


if __name__ == "__main__":
    main()
