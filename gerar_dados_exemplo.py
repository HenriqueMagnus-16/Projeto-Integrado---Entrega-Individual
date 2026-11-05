"""
Gera uma base SINTÉTICA (dados fictícios aproximados) apenas para TESTAR o código.
NÃO são dados reais do IBGE. Para o trabalho, substitua por dados do Censo 2022
(SIDRA/IBGE: população residente por cor ou raça, sexo e grupos de idade, por UF).

Uso:  python gerar_dados_exemplo.py
Saída: dados/base_exemplo_sintetica.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

# UF: (população aproximada em milhões, % preta+parda aproximado, índice de "envelhecimento" 0-1)
UFS = {
    "AC": (0.83, 0.74, 0.25), "AL": (3.1, 0.67, 0.40), "AP": (0.73, 0.77, 0.20),
    "AM": (3.9, 0.76, 0.25), "BA": (14.1, 0.80, 0.48), "CE": (8.8, 0.68, 0.48),
    "DF": (2.8, 0.58, 0.45), "ES": (3.8, 0.60, 0.52), "GO": (7.1, 0.60, 0.46),
    "MA": (6.8, 0.82, 0.38), "MT": (3.7, 0.62, 0.38), "MS": (2.8, 0.52, 0.45),
    "MG": (20.5, 0.57, 0.58), "PA": (8.1, 0.82, 0.32), "PB": (4.0, 0.62, 0.52),
    "PR": (11.4, 0.34, 0.56), "PE": (9.0, 0.66, 0.50), "PI": (3.3, 0.78, 0.46),
    "RJ": (16.0, 0.52, 0.68), "RN": (3.3, 0.62, 0.50), "RS": (10.9, 0.21, 0.72),
    "RO": (1.6, 0.66, 0.35), "RR": (0.64, 0.70, 0.17), "SC": (7.6, 0.19, 0.55),
    "SP": (44.4, 0.42, 0.62), "SE": (2.2, 0.73, 0.43), "TO": (1.5, 0.73, 0.33),
}
FAIXAS = [f"{i} a {i+4} anos" for i in range(0, 80, 5)] + ["80 anos ou mais"]
RACAS = ["Branca", "Preta", "Amarela", "Parda", "Indígena"]
SEXOS = ["Homens", "Mulheres"]

linhas = []
for uf, (pop_mi, pct_neg, env) in UFS.items():
    # pirâmide: quanto maior 'env', mais "achatada" a base
    idades = np.arange(len(FAIXAS))
    peso_idade = np.exp(-idades * (0.20 - 0.10 * env)) * (1 + 0.04 * idades * env)
    peso_idade /= peso_idade.sum()
    pretos = 0.10 * pct_neg
    pardos = pct_neg - pretos
    resto = 1 - pct_neg
    peso_raca = np.array([resto * 0.985, pretos, resto * 0.005, pardos, resto * 0.010])
    peso_raca /= peso_raca.sum()
    for s, fs in zip(SEXOS, (0.485, 0.515)):
        for r, pr in zip(RACAS, peso_raca):
            for i, fx in enumerate(FAIXAS):
                # pessoas negras são, em média, mais jovens; brancas mais velhas
                ajuste = 1.0
                if r in ("Preta", "Parda"):
                    ajuste = 1.25 - 0.045 * i
                elif r == "Branca":
                    ajuste = 0.80 + 0.035 * i
                ajuste = max(ajuste, 0.2)
                mulher_idoso = 1.0 + (0.012 * i if s == "Mulheres" else 0)
                v = pop_mi * 1e6 * fs * pr * peso_idade[i] * ajuste * mulher_idoso
                v *= rng.normal(1, 0.03)
                linhas.append([2022, uf, s, r, fx, max(int(v), 0)])

df = pd.DataFrame(linhas, columns=["ano", "uf", "sexo", "raca_cor", "faixa_etaria", "populacao"])
saida = Path(__file__).parent / "dados" / "base_exemplo_sintetica.csv"
saida.parent.mkdir(exist_ok=True)
df.to_csv(saida, index=False, encoding="utf-8")
print(f"Gerado {saida} com {len(df)} linhas (DADOS SINTÉTICOS, só para teste).")
