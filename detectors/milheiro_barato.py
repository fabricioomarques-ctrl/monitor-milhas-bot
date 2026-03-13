def detectar_milheiro_barato(resultados):

    novos = []

    for r in resultados:

        texto = (r["titulo"] + r["detalhe"]).lower()

        if "milheiro" in texto and "r$" in texto:

            novos.append({
                "tipo": "milheiro_barato",
                "titulo": r["titulo"],
                "link": r["link"],
                "fonte": r["fonte"],
                "detalhe": "Possível milheiro barato"
            })

    return novos
