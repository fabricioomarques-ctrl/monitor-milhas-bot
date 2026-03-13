from collectors.blogs import coletar_blogs
from collectors.programas import coletar_programas
from collectors.bancos import coletar_bancos
from collectors.milheiro import coletar_milheiro
from collectors.social import coletar_social

from detectors.noise_filter import is_noise
from detectors.transferencias import detectar_transferencia
from detectors.passagens import detectar_passagem
from detectors.milheiro_barato import detectar_milheiro_barato

from engine.confirmador import confirmar_multi_fonte
from engine.metrics import (
    criar_metrics_execucao,
    registrar_fontes,
    registrar_coleta,
    registrar_descarte,
    registrar_detectados,
    registrar_resultados,
    registrar_erro,
    salvar_metrics,
)
from engine.scoring import ordenar_resultados


def coletar_tudo() -> tuple[list[dict], list[dict]]:
    dados = []
    fontes_meta = []

    for coletor in [
        coletar_blogs,
        coletar_programas,
        coletar_bancos,
        coletar_milheiro,
        coletar_social,
    ]:
        itens, fontes = coletor()
        dados.extend(itens)
        fontes_meta.extend(fontes)

    return dados, fontes_meta


def detectar_oportunidades(dados_brutos: list[dict], metrics: dict) -> list[dict]:
    oportunidades = []

    for item in dados_brutos:
        combinado = f"{item.get('titulo', '')} {item.get('texto', '')}"

        if is_noise(combinado):
            registrar_descarte(metrics, "ruido")
            continue

        achou = False

        transferencia = detectar_transferencia(item)
        if transferencia:
            oportunidades.append(transferencia)
            achou = True

        passagem = detectar_passagem(item)
        if passagem:
            oportunidades.append(passagem)
            achou = True

        milheiro = detectar_milheiro_barato(item)
        if milheiro:
            oportunidades.append(milheiro)
            achou = True

        if not achou:
            registrar_descarte(metrics, "sem_match_detector")

    return oportunidades


def executar_radar() -> tuple[list[dict], dict]:
    metrics = criar_metrics_execucao()

    try:
        dados_brutos, fontes_meta = coletar_tudo()
        registrar_fontes(metrics, fontes_meta)
        registrar_coleta(metrics, len(dados_brutos))

        oportunidades = detectar_oportunidades(dados_brutos, metrics)
        oportunidades = confirmar_multi_fonte(oportunidades)
        oportunidades = ordenar_resultados(oportunidades)

        registrar_detectados(metrics, len(oportunidades))
        registrar_resultados(metrics, oportunidades)
        salvar_metrics(metrics)

        return oportunidades, metrics

    except Exception as e:
        registrar_erro(metrics, str(e))
        salvar_metrics(metrics)
        raise
