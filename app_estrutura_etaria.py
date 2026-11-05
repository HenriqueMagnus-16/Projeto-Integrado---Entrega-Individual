"""
Seção Streamlit - Aluno 1: Estrutura Etária, Sexo e Raça (com foco em mobilidade)
Rodar:  streamlit run app_estrutura_etaria.py

Para integrar ao painel do grupo, chame `render()` dentro da página do menu lateral.
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import modulo_estrutura_etaria as m

BASE_EXEMPLO = Path(__file__).parent / "dados" / "base_exemplo_sintetica.csv"


@st.cache_data(show_spinner=False)
def _carregar_exemplo() -> pd.DataFrame:
    return m.tratar_dados(pd.read_csv(BASE_EXEMPLO))


def render():
    st.title("👶 Estrutura Etária, Sexo e Raça")
    st.caption("Leitura demográfica para a pauta de mobilidade urbana e transporte público.")

    # ------------------------------------------------------------ Sidebar
    st.sidebar.header("Dados e filtros")
    arq = st.sidebar.file_uploader("Base do IBGE (CSV/XLSX)", type=["csv", "xlsx"])
    usando_exemplo = arq is None
    try:
        if usando_exemplo:
            if not BASE_EXEMPLO.exists():
                st.error("Envie um arquivo ou rode `python gerar_dados_exemplo.py` para criar a base de teste.")
                st.stop()
            df = _carregar_exemplo()
            st.warning("Usando base SINTÉTICA de teste. Envie a base real do IBGE na barra lateral.")
        else:
            df = m.tratar_dados(m.carregar_base(arq))
            st.sidebar.success(f"{len(df):,} linhas carregadas".replace(",", "."))
    except Exception as e:  # mensagem amigável para erro de upload
        st.error(f"Não foi possível processar o arquivo: {e}")
        st.stop()

    anos = st.sidebar.multiselect("Ano", sorted(df["ano"].unique()), default=sorted(df["ano"].unique())[-1:])
    regioes = st.sidebar.multiselect("Região", sorted(df["regiao"].unique()))
    ufs_disp = sorted(df[df["regiao"].isin(regioes)]["uf"].unique()) if regioes else sorted(df["uf"].unique())
    ufs = st.sidebar.multiselect("UF", ufs_disp)
    sexos = st.sidebar.multiselect("Sexo", sorted(df["sexo"].unique()))
    racas = st.sidebar.multiselect("Raça/Cor", sorted(df["raca_cor"].unique()))
    ordem_faixas = df.drop_duplicates("faixa_etaria").sort_values("idade_inicial")["faixa_etaria"].tolist()
    faixas = st.sidebar.multiselect("Faixa etária", ordem_faixas)

    f = m.filtrar(df, ufs, regioes, sexos, racas, faixas, anos)
    if f.empty:
        st.info("Nenhum dado para os filtros escolhidos.")
        st.stop()

    # Indicadores por UF: calculados com filtros de território/ano (todas as faixas/raças/sexos),
    # senão os percentuais perderiam sentido.
    base_ind = m.filtrar(df, ufs, regioes, None, None, None, anos)
    ind = m.indicadores_por_uf(base_ind)

    # ------------------------------------------------------------ KPIs
    pop = f["populacao"].sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("População (filtro)", f"{pop:,.0f}".replace(",", "."))
    c2.metric("% idosos (60+) - média UFs", f"{ind['pct_idosos_60mais'].mean():.1f}%")
    c3.metric("% jovens (15-29) - média UFs", f"{ind['pct_jovens_15_29'].mean():.1f}%")
    c4.metric("% preta e parda - média UFs", f"{ind['pct_preta_parda'].mean():.1f}%")

    aba1, aba2, aba3, aba4, aba5 = st.tabs(
        ["Pirâmide etária", "Raça e idade", "Estatísticas", "Outliers", "Análise e mídia"])

    # ------------------------------------------------------------ Pirâmide
    with aba1:
        p = m.piramide_etaria(f)
        p["valor"] = p.apply(lambda r: -r["populacao"] if r["sexo"].lower().startswith("h") else r["populacao"], axis=1)
        fig = px.bar(p, x="valor", y="faixa_etaria", color="sexo", orientation="h",
                     category_orders={"faixa_etaria": ordem_faixas},
                     labels={"valor": "População", "faixa_etaria": "Faixa etária"},
                     title="Pirâmide etária por sexo")
        fig.update_layout(barmode="relative", yaxis={"categoryorder": "array", "categoryarray": ordem_faixas})
        st.plotly_chart(fig, use_container_width=True)

    # ------------------------------------------------------------ Raça x idade
    with aba2:
        g = f.groupby(["grupo_amplo", "raca_cor"])["populacao"].sum().reset_index()
        g["pct_no_grupo"] = 100 * g["populacao"] / g.groupby("grupo_amplo")["populacao"].transform("sum")
        ordem = ["Crianças (0-14)", "Jovens (15-29)", "Adultos (30-59)", "Idosos (60+)"]
        fig = px.bar(g, x="grupo_amplo", y="pct_no_grupo", color="raca_cor",
                     category_orders={"grupo_amplo": ordem},
                     labels={"pct_no_grupo": "% dentro do grupo etário", "grupo_amplo": ""},
                     title="Composição racial de cada grupo etário")
        st.plotly_chart(fig, use_container_width=True)

        top = ind.sort_values("pct_idosos_60mais", ascending=False)
        fig2 = px.bar(top, x="uf", y="pct_idosos_60mais", color="regiao",
                      labels={"pct_idosos_60mais": "% idosos (60+)"}, title="Envelhecimento por UF")
        st.plotly_chart(fig2, use_container_width=True)

        fig3 = px.scatter(ind, x="pct_jovens_15_29", y="pct_idosos_60mais", color="regiao",
                          size="populacao_total", hover_name="uf",
                          labels={"pct_jovens_15_29": "% jovens", "pct_idosos_60mais": "% idosos"},
                          title="Jovens x Idosos por UF (tamanho = população)")
        st.plotly_chart(fig3, use_container_width=True)

    # ------------------------------------------------------------ Estatísticas
    with aba3:
        cols = {"pct_idosos_60mais": "% idosos (60+)", "pct_jovens_15_29": "% jovens (15-29)",
                "pct_preta_parda": "% preta e parda", "indice_envelhecimento": "Índice de envelhecimento",
                "razao_sexo": "Razão de sexo"}
        tabela = m.tabela_estatisticas(ind, list(cols)).rename(columns=cols)
        st.dataframe(tabela.style.format("{:.2f}"), use_container_width=True)
        st.caption("Variância e desvio padrão amostrais (ddof=1). Moda calculada com 1 casa decimal. "
                   "Cada observação é uma UF.")
        escolha = st.selectbox("Indicador para o histograma/boxplot", list(cols), format_func=cols.get)
        a, b = st.columns(2)
        a.plotly_chart(px.histogram(ind, x=escolha, nbins=10, title="Histograma"), use_container_width=True)
        b.plotly_chart(px.box(ind, y=escolha, points="all", hover_name="uf", title="Boxplot"),
                       use_container_width=True)

    # ------------------------------------------------------------ Outliers
    with aba4:
        escolha2 = st.selectbox("Indicador", list(cols), format_func=cols.get, key="out")
        est = m.estatisticas_descritivas(ind[escolha2])
        st.write(f"Limites 1,5×IQR: **{est['limite_inferior']:.2f}** a **{est['limite_superior']:.2f}** "
                 f"(Q1={est['q1']:.2f}, Q3={est['q3']:.2f}, IQR={est['iqr']:.2f})")
        out = m.detectar_outliers(ind, escolha2)
        if out.empty:
            st.success("Nenhum outlier pela regra 1,5×IQR.")
        else:
            st.dataframe(out, use_container_width=True)
        st.caption("Compare média x mediana: se há outliers, a média é puxada para o lado do extremo.")
        st.markdown("**Tabela por UF**")
        st.dataframe(ind.drop(columns=["jovens", "idosos", "criancas", "negros", "jovens_negros",
                                       "idosos_negros", "homens", "mulheres"]).round(2),
                     use_container_width=True)

    # ------------------------------------------------------------ Análise
    with aba5:
        st.subheader("Texto analítico (gerado dos dados)")
        st.write(m.texto_analitico(ind))
        st.subheader("Leitura para a mobilidade urbana")
        st.markdown(
            "- A base mostra **estrutura demográfica**, não o uso de transporte. A ligação com o ônibus vem "
            "da literatura (IPEA, TD 2739) e deve ser citada como tal na apresentação.\n"
            "- UFs com maior % de jovens pretos e pardos tendem a concentrar demanda por transporte coletivo.\n"
            "- UFs com maior índice de envelhecimento exigem acessibilidade: ônibus de piso baixo, pontos "
            "cobertos, integração e gratuidade efetiva.")
        st.subheader("Notícias e mídia (opcional)")
        st.info("Cole aqui links/imagens de notícias reais sobre mobilidade e envelhecimento. "
                "Ex.: st.image('imagem.jpg'), st.markdown('[Título](URL)').")


if __name__ == "__main__":
    st.set_page_config(page_title="Estrutura Etária", layout="wide")
    render()
