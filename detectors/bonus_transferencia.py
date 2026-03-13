def detectar_bonus_transferencia(resultados):

    novos = []

    for r in resultados:

        texto = (r["titulo"] + r["detalhe"]).lower()

        if "bônus" in texto or "bonus" in texto:

            novos.append({
                "tipo": "bonus_alto",
                "titulo": r["titulo"],
                "link": r["link"],
                "fonte": r["fonte"],
                "detalhe": "Possível bônus de transferência"
            })

    return novos
