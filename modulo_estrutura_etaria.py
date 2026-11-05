"""
Módulo individual - Aluno 1
Indicador: População por Grupo de Idade, Sexo e Raça (estrutura etária)
Projeto Integrador "Números que Falam" - Python & Matemática

Contém:
  1. ETL (leitura CSV/XLSX, padronização, limpeza, filtros)
  2. Indicadores derivados por UF (% jovens, % idosos, % pretos e pardos, etc.)
  3. Estatísticas descritivas (média, mediana, moda, Q1-Q3, IQR, amplitude,
     variância, desvio padrão) e detecção de outliers pela regra 1,5 x IQR

Formato esperado da base (uma linha por UF x sexo x raça/cor x faixa etária):
    uf | sexo | raca_cor | faixa_etaria | populacao      (+ opcional: ano, regiao)
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Constantes
# --------------------------------------------------------------------------
REGIAO_POR_UF = {
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte", "RO": "Norte",
    "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste",
    "SE": "Nordeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste",
    "MS": "Centro-Oeste",
}

COLUNAS_OBRIGATORIAS = ["uf", "sexo", "raca_cor", "faixa_etaria", "populacao"]

# Sinônimos comuns de colunas em arquivos baixados do IBGE/SIDRA
SINONIMOS_COLUNAS = {
    "uf": ["uf", "sigla_uf", "unidade_da_federacao", "unidade_federativa", "estado"],
    "sexo": ["sexo"],
    "raca_cor": ["raca_cor", "cor_ou_raca", "cor_raca", "raca", "cor"],
    "faixa_etaria": ["faixa_etaria", "grupo_de_idade", "grupos_de_idade",
                     "grupo_idade", "idade", "faixa_de_idade"],
    "populacao": ["populacao", "valor", "pessoas", "populacao_residente", "total"],
    "ano": ["ano"],
    "regiao": ["regiao", "grande_regiao"],
}

NEGROS = ["Preta", "Parda"]  # população negra = preta + parda (convenção IBGE/IPEA)


# --------------------------------------------------------------------------
# 1. ETL
# --------------------------------------------------------------------------
def _normalizar_nome(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", str(txt)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", txt.lower()).strip("_")


def carregar_base(arquivo) -> pd.DataFrame:
    """Lê CSV ou XLSX (caminho ou objeto de upload do Streamlit)."""
    nome = getattr(arquivo, "name", str(arquivo)).lower()
    if nome.endswith((".xlsx", ".xlsm", ".xls")):
        return pd.read_excel(arquivo)
    if nome.endswith((".csv", ".txt")):
        for enc in ("utf-8-sig", "latin-1"):
            try:
                if hasattr(arquivo, "seek"):
                    arquivo.seek(0)
                return pd.read_csv(arquivo, sep=None, engine="python", encoding=enc)
            except UnicodeDecodeError:
                continue
    raise ValueError("Formato não suportado. Envie um arquivo .csv ou .xlsx.")


def _numero_br(serie: pd.Series) -> pd.Series:
    """Converte '1.234.567' / '1234,5' / '-' / '...' em número."""
    if pd.api.types.is_numeric_dtype(serie):
        return serie.astype(float)
    s = (serie.astype(str).str.strip()
         .replace({"-": np.nan, "...": np.nan, "X": np.nan, "": np.nan, "nan": np.nan}))
    s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def idade_inicial(faixa: str) -> float:
    """Extrai a idade inicial de rótulos como '0 a 4 anos', '80 anos ou mais'."""
    m = re.search(r"\d+", str(faixa))
    return float(m.group()) if m else np.nan


def grupo_amplo(idade_ini: float) -> str:
    if np.isnan(idade_ini):
        return "Indefinido"
    if idade_ini < 15:
        return "Crianças (0-14)"
    if idade_ini < 30:
        return "Jovens (15-29)"
    if idade_ini < 60:
        return "Adultos (30-59)"
    return "Idosos (60+)"


def tratar_dados(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza colunas, limpa textos, converte números e remove inconsistências."""
    df = df.copy()
    df.columns = [_normalizar_nome(c) for c in df.columns]

    # mapear sinônimos -> nomes padrão
    renomear = {}
    for padrao, opcoes in SINONIMOS_COLUNAS.items():
        for op in opcoes:
            if op in df.columns and padrao not in renomear.values():
                renomear[op] = padrao
                break
    df = df.rename(columns=renomear)

    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise ValueError(f"Colunas obrigatórias ausentes: {faltando}. "
                         f"Colunas encontradas: {list(df.columns)}")

    for col in ["uf", "sexo", "raca_cor", "faixa_etaria"]:
        df[col] = df[col].astype(str).str.strip()
    df["uf"] = df["uf"].str.upper()
    df["sexo"] = df["sexo"].str.capitalize()
    df["raca_cor"] = df["raca_cor"].str.capitalize()

    df["populacao"] = _numero_br(df["populacao"])
    df = df.dropna(subset=["populacao"])
    df = df[df["populacao"] >= 0]

    # remove linhas de totais (ex.: "Total", "Ambos") para não duplicar contagem
    termos_total = ["total", "ambos"]
    for col in ["sexo", "raca_cor", "faixa_etaria", "uf"]:
        df = df[~df[col].str.lower().isin(termos_total)]

    if "regiao" not in df.columns:
        df["regiao"] = df["uf"].map(REGIAO_POR_UF)
    df["regiao"] = df["regiao"].fillna("Não identificada")
    if "ano" not in df.columns:
        df["ano"] = 2022
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").fillna(2022).astype(int)

    df["idade_inicial"] = df["faixa_etaria"].map(idade_inicial)
    df["grupo_amplo"] = df["idade_inicial"].map(grupo_amplo)
    df = df.drop_duplicates(subset=["ano", "uf", "sexo", "raca_cor", "faixa_etaria"])
    return df.sort_values(["ano", "uf", "sexo", "raca_cor", "idade_inicial"]).reset_index(drop=True)


def filtrar(df: pd.DataFrame, ufs: Iterable[str] | None = None,
            regioes: Iterable[str] | None = None, sexos: Iterable[str] | None = None,
            racas: Iterable[str] | None = None, faixas: Iterable[str] | None = None,
            anos: Iterable[int] | None = None) -> pd.DataFrame:
    """Aplica filtros (lista vazia/None = sem filtro naquela dimensão)."""
    out = df
    for col, vals in [("uf", ufs), ("regiao", regioes), ("sexo", sexos),
                      ("raca_cor", racas), ("faixa_etaria", faixas), ("ano", anos)]:
        if vals:
            out = out[out[col].isin(list(vals))]
    return out


# --------------------------------------------------------------------------
# 2. Indicadores derivados por UF
# --------------------------------------------------------------------------
def indicadores_por_uf(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por UF com os indicadores usados na análise estatística."""
    if df.empty:
        return pd.DataFrame()
    total = df.groupby("uf")["populacao"].sum().rename("populacao_total")

    def soma(mask):
        return df[mask].groupby("uf")["populacao"].sum()

    jovens = soma(df["grupo_amplo"] == "Jovens (15-29)")
    idosos = soma(df["grupo_amplo"] == "Idosos (60+)")
    criancas = soma(df["grupo_amplo"] == "Crianças (0-14)")
    negros = soma(df["raca_cor"].isin(NEGROS))
    jovens_negros = soma((df["grupo_amplo"] == "Jovens (15-29)") & df["raca_cor"].isin(NEGROS))
    idosos_negros = soma((df["grupo_amplo"] == "Idosos (60+)") & df["raca_cor"].isin(NEGROS))
    homens = soma(df["sexo"].str.lower() == "homens") if (df["sexo"].str.lower() == "homens").any() \
        else soma(df["sexo"].str.lower().str.startswith("h"))
    mulheres = soma(df["sexo"].str.lower().str.startswith("m"))

    res = pd.concat({
        "populacao_total": total, "jovens": jovens, "idosos": idosos,
        "criancas": criancas, "negros": negros, "jovens_negros": jovens_negros,
        "idosos_negros": idosos_negros, "homens": homens, "mulheres": mulheres,
    }, axis=1).fillna(0)

    res["pct_jovens_15_29"] = 100 * res["jovens"] / res["populacao_total"]
    res["pct_idosos_60mais"] = 100 * res["idosos"] / res["populacao_total"]
    res["pct_preta_parda"] = 100 * res["negros"] / res["populacao_total"]
    res["pct_jovens_que_sao_negros"] = 100 * res["jovens_negros"] / res["jovens"].replace(0, np.nan)
    res["pct_idosos_que_sao_negros"] = 100 * res["idosos_negros"] / res["idosos"].replace(0, np.nan)
    res["indice_envelhecimento"] = 100 * res["idosos"] / res["criancas"].replace(0, np.nan)
    res["razao_sexo"] = 100 * res["homens"] / res["mulheres"].replace(0, np.nan)
    res["regiao"] = res.index.map(REGIAO_POR_UF)
    return res.reset_index().rename(columns={"index": "uf"})


# --------------------------------------------------------------------------
# 3. Estatísticas descritivas e outliers
# --------------------------------------------------------------------------
def estatisticas_descritivas(serie: pd.Series) -> dict:
    """Medidas obrigatórias do projeto para uma série numérica."""
    x = pd.to_numeric(serie, errors="coerce").dropna()
    if x.empty:
        return {}
    q1, q2, q3 = x.quantile([0.25, 0.50, 0.75])
    iqr = q3 - q1
    lim_inf, lim_sup = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    moda = x.round(1).mode()
    n = len(x)
    return {
        "n": n,
        "media": x.mean(),
        "mediana": x.median(),
        "moda": moda.iloc[0] if not moda.empty else np.nan,
        "minimo": x.min(),
        "q1": q1, "q2": q2, "q3": q3,
        "maximo": x.max(),
        "iqr": iqr,
        "amplitude": x.max() - x.min(),
        "variancia": x.var(ddof=1) if n > 1 else np.nan,       # amostral
        "desvio_padrao": x.std(ddof=1) if n > 1 else np.nan,   # amostral
        "coef_variacao_pct": 100 * x.std(ddof=1) / x.mean() if n > 1 and x.mean() else np.nan,
        "assimetria": x.skew() if n > 2 else np.nan,
        "limite_inferior": lim_inf,
        "limite_superior": lim_sup,
        "n_outliers": int(((x < lim_inf) | (x > lim_sup)).sum()),
    }


def detectar_outliers(df: pd.DataFrame, coluna: str, rotulo: str = "uf") -> pd.DataFrame:
    """Retorna as linhas fora de [Q1 - 1,5 IQR ; Q3 + 1,5 IQR]."""
    est = estatisticas_descritivas(df[coluna])
    if not est:
        return df.iloc[0:0]
    mask = (df[coluna] < est["limite_inferior"]) | (df[coluna] > est["limite_superior"])
    out = df.loc[mask, [rotulo, coluna]].copy()
    out["tipo"] = np.where(out[coluna] > est["limite_superior"], "acima", "abaixo")
    return out.sort_values(coluna, ascending=False)


def tabela_estatisticas(ind: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Tabela com as estatísticas de várias colunas (uma coluna por indicador)."""
    return pd.DataFrame({c: estatisticas_descritivas(ind[c]) for c in colunas})


def piramide_etaria(df: pd.DataFrame) -> pd.DataFrame:
    """População por faixa etária x sexo (base da pirâmide etária)."""
    p = (df.groupby(["idade_inicial", "faixa_etaria", "sexo"])["populacao"]
           .sum().reset_index().sort_values("idade_inicial"))
    return p


def texto_analitico(ind: pd.DataFrame) -> str:
    """Gera um texto interpretativo a partir dos números (rascunho da análise)."""
    if ind.empty:
        return "Sem dados para os filtros selecionados."
    e_id = estatisticas_descritivas(ind["pct_idosos_60mais"])
    e_jv = estatisticas_descritivas(ind["pct_jovens_15_29"])
    e_neg = estatisticas_descritivas(ind["pct_preta_parda"])
    out_id = detectar_outliers(ind, "pct_idosos_60mais")
    out_neg = detectar_outliers(ind, "pct_preta_parda")
    maior = ind.loc[ind["pct_idosos_60mais"].idxmax()]
    menor = ind.loc[ind["pct_idosos_60mais"].idxmin()]
    linhas = [
        f"Entre as {e_id['n']} UFs analisadas, a participação média de idosos (60+) é "
        f"{e_id['media']:.1f}% (mediana {e_id['mediana']:.1f}%, desvio padrão "
        f"{e_id['desvio_padrao']:.2f} p.p.). A maior é {maior['uf']} ({maior['pct_idosos_60mais']:.1f}%) "
        f"e a menor é {menor['uf']} ({menor['pct_idosos_60mais']:.1f}%), amplitude de "
        f"{e_id['amplitude']:.1f} p.p.: o envelhecimento é desigual entre os territórios.",
        f"Os jovens (15-29) representam em média {e_jv['media']:.1f}% da população "
        f"(IQR = {e_jv['iqr']:.2f} p.p.). A população preta e parda é, em média, "
        f"{e_neg['media']:.1f}% (mediana {e_neg['mediana']:.1f}%).",
    ]
    if not out_id.empty:
        linhas.append("Outliers de envelhecimento (regra 1,5×IQR): "
                      + ", ".join(f"{r.uf} ({r.pct_idosos_60mais:.1f}%)" for r in out_id.itertuples()) + ".")
    else:
        linhas.append("Não há outliers de envelhecimento pela regra 1,5×IQR.")
    if not out_neg.empty:
        linhas.append("Outliers de composição racial: "
                      + ", ".join(f"{r.uf} ({r.pct_preta_parda:.1f}%)" for r in out_neg.itertuples()) + ".")
    return " ".join(linhas)
