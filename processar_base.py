"""
Gera os dois entregáveis individuais a partir da base BRUTA do IBGE:
  - dados/base_tratada.csv       (base IBGE tratada)
  - analise_descritiva.md        (tabelas + texto analítico para você revisar)

Uso:  python processar_base.py caminho/da/base_ibge.csv   (ou .xlsx)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import modulo_estrutura_etaria as m

COLS = {
    "pct_idosos_60mais": "% idosos (60+)",
    "pct_jovens_15_29": "% jovens (15-29)",
    "pct_preta_parda": "% preta e parda",
    "indice_envelhecimento": "Índice de envelhecimento",
    "razao_sexo": "Razão de sexo",
}


def md_tabela(df: pd.DataFrame, casas: int = 2) -> str:
    cab = "| " + " | ".join([""] + [str(c) for c in df.columns]) + " |"
    sep = "|" + "---|" * (len(df.columns) + 1)
    linhas = []
    for idx, row in df.iterrows():
        vals = [f"{v:.{casas}f}" if isinstance(v, (int, float, np.floating)) and pd.notna(v) else str(v)
                for v in row]
        linhas.append("| " + " | ".join([str(idx)] + vals) + " |")
    return "\n".join([cab, sep] + linhas)


def main(caminho: str):
    raiz = Path(__file__).parent
    bruto = m.carregar_base(Path(caminho).open("rb") if caminho.lower().endswith((".xlsx", ".xls")) else open(caminho, "rb"))
    df = m.tratar_dados(bruto)

    (raiz / "dados").mkdir(exist_ok=True)
    df.to_csv(raiz / "dados" / "base_tratada.csv", index=False, encoding="utf-8")

    ind = m.indicadores_por_uf(df)
    tab = m.tabela_estatisticas(ind, list(COLS)).rename(columns=COLS)
    mostrar = tab.loc[["n", "media", "mediana", "moda", "q1", "q3", "iqr", "amplitude",
                       "variancia", "desvio_padrao", "limite_inferior", "limite_superior", "n_outliers"]]

    aviso = ""
    if "sintetica" in caminho.lower() or "exemplo" in caminho.lower():
        aviso = "> ATENÇÃO: esta análise foi gerada com a base SINTÉTICA de teste. Não entregue assim.\n\n"

    partes = [
        "# Análise descritiva - Estrutura etária, sexo e raça (Aluno 1)\n",
        aviso,
        f"Base: {len(df)} linhas, {df['uf'].nunique()} UFs, ano(s) {', '.join(str(int(a)) for a in sorted(df['ano'].unique()))}. "
        "Cada observação estatística é uma UF.\n",
        "## 1. Medidas estatísticas\n",
        md_tabela(mostrar),
        "\n## 2. Leitura automática dos números\n",
        m.texto_analitico(ind),
        "\n## 3. Outliers (regra 1,5×IQR)\n",
    ]
    for col, nome in COLS.items():
        out = m.detectar_outliers(ind, col)
        if out.empty:
            partes.append(f"- {nome}: nenhum outlier.")
        else:
            partes.append(f"- {nome}: " + ", ".join(f"{r.uf} ({getattr(r, col):.1f}, {r.tipo})" for r in out.itertuples()))
    partes += [
        "\n## 4. Interpretação social (EDITE COM SUAS PALAVRAS)\n",
        "- Desigualdade territorial: compare as UFs mais e menos envelhecidas e explique a amplitude e o desvio padrão.",
        "- Raça e idade: a população preta e parda é mais jovem que a branca? Cite % de jovens e de idosos que são negros (colunas `pct_jovens_que_sao_negros` e `pct_idosos_que_sao_negros` da tabela por UF).",
        "- Média x mediana: diga se algum outlier distorce a média.",
        "- Mobilidade (argumento da roda): a base mostra estrutura demográfica, não uso de ônibus. Cite o IPEA (TD 2739) para a ligação com transporte público e use o envelhecimento do Censo para justificar a adaptação da frota.",
    ]
    (raiz / "analise_descritiva.md").write_text("\n".join(partes), encoding="utf-8")
    print("Gerados: dados/base_tratada.csv e analise_descritiva.md")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Uso: python processar_base.py caminho/da/base_ibge.csv")
    main(sys.argv[1])
