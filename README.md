# Projeto Integrador - Números que Falam (Aluno 1)

**Indicador:** População por grupo de idade, sexo e raça (estrutura etária), com foco em mobilidade urbana.

## Arquivos
- `modulo_estrutura_etaria.py`: ETL + estatísticas (média, mediana, moda, Q1-Q3, IQR, amplitude, variância, desvio padrão, outliers 1,5×IQR).
- `app_estrutura_etaria.py`: seção Streamlit (upload, filtros, KPIs, pirâmide, boxplot, histograma, outliers, texto analítico).
- `gerar_dados_exemplo.py`: gera base **sintética** só para testar. Não usar na entrega.
- `requirements.txt`: dependências.

## Como rodar
```bash
pip install -r requirements.txt
python gerar_dados_exemplo.py          # opcional (base de teste)
streamlit run app_estrutura_etaria.py
```

## Formato da base
Colunas: `uf, sexo, raca_cor, faixa_etaria, populacao` (opcionais: `ano, regiao`).
Nomes parecidos do IBGE/SIDRA (ex.: "Cor ou raça", "Grupo de idade", "Valor") são reconhecidos automaticamente.
Linhas de "Total" são removidas no tratamento.

## Dados reais
Censo 2022 (IBGE/SIDRA): população residente por cor ou raça, sexo e grupos de idade, por UF.
Exporte em CSV/XLSX, faça o upload na barra lateral e salve a versão tratada para a entrega.

## Integração com o grupo
No painel unificado: `import app_estrutura_etaria as a1` e chame `a1.render()` na página do menu.
Cuidado: `st.set_page_config` só deve ser chamado uma vez, no arquivo principal.
