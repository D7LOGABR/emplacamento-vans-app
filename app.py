import streamlit as st
import pandas as pd
import plotly.express as px
from dateutil.relativedelta import relativedelta
from collections import Counter
import os
from io import BytesIO

# --- Configuração da Página ---
st.set_page_config(
    page_title="Emplacamentos VANS De Nigris",
    page_icon="🚚", # Consider changing icon to a van?
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Estilo CSS Customizado ---
st.markdown("""
<style>
    /* Ajustar padding do container principal */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }
    /* Estilo para os cards de informação */
    .info-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 5px solid #0055a4; /* Azul De Nigris */
    }
    .info-card .label {
        font-weight: bold;
        color: #003366; /* Azul escuro De Nigris */
        display: block;
        margin-bottom: 3px;
    }
    .info-card .value {
        color: #333;
    }
    /* Títulos */
    h1, h2, h3, h4 {
        color: #003366; /* Azul escuro De Nigris */
    }
    /* Botão de busca */
    .stButton>button {
        background-color: #0055a4; /* Azul De Nigris */
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
    }
    .stButton>button:hover {
        background-color: #003366;
        color: white;
    }
    /* Mensagens de erro/info */
    .stAlert p {
        font-size: 1rem; /* Ajustar tamanho da fonte nas mensagens */
    }
    /* Estilo para métricas de resumo */
    .stMetric {
        background-color: #e9ecef;
        border-radius: 8px;
        padding: 10px 15px;
        border-left: 5px solid #6c757d; /* Cinza */
    }
</style>
""", unsafe_allow_html=True)

# --- Constantes e Caminhos ---
DATA_DIR = "data"
DEFAULT_EXCEL_FILE = os.path.join(DATA_DIR, "EMPLACAMENTO ANUAL - VANS.xlsx")
LOGO_COLOR_PATH = os.path.join(DATA_DIR, "logo_denigris_colorido.png")
LOGO_WHITE_PATH = os.path.join(DATA_DIR, "logo_denigris_branco.png")

# --- Nomes das Colunas Opcionais (Definidos Globalmente) ---
NOME_COLUNA_ENDERECO = "ENDEREÇO COMPLETO"
NOME_COLUNA_TELEFONE = "TELEFONE1" # Nome da coluna de telefone definido

# --- Funções de Carregamento de Dados ---
# @st.cache_data # Cache pode ser reativado se a performance for um problema, mas pode interferir com o upload
def load_data(file_path_or_buffer):
    """Carrega e pré-processa os dados do arquivo Excel."""
    try:
        df = pd.read_excel(file_path_or_buffer)

        # Limpeza e conversão de tipos (com dayfirst=True)
        df["Data emplacamento"] = pd.to_datetime(df["Data emplacamento"], errors="coerce", dayfirst=True)
        df["CNPJ CLIENTE"] = df["CNPJ CLIENTE"].astype(str).str.strip()
        df["NOME DO CLIENTE"] = df["NOME DO CLIENTE"].astype(str).str.strip()

        # Processar colunas opcionais usando nomes globais
        if NOME_COLUNA_ENDERECO in df.columns:
            df[NOME_COLUNA_ENDERECO] = df[NOME_COLUNA_ENDERECO].astype(str).str.strip()
        else:
            df[NOME_COLUNA_ENDERECO] = "N/A"

        if NOME_COLUNA_TELEFONE in df.columns:
            df[NOME_COLUNA_TELEFONE] = df[NOME_COLUNA_TELEFONE].astype(str).str.strip()
        else:
            df[NOME_COLUNA_TELEFONE] = "N/A"

        # Garantir que colunas essenciais para análise existam
        for col in ["Marca", "Segmento", "NO_CIDADE", "Data emplacamento"]:
             if col not in df.columns:
                  st.error(f"Erro: Coluna essencial 	'{col}	' não encontrada no arquivo Excel.")
                  return None

        df["CNPJ_NORMALIZED"] = df["CNPJ CLIENTE"].str.replace(r"[.\\/-]", "", regex=True)
        df["Ano"] = df["Data emplacamento"].dt.year
        df["Mes"] = df["Data emplacamento"].dt.month
        df["AnoMesNum"] = df["Data emplacamento"].dt.strftime("%Y%m").astype(int) # Para ordenação
        df["AnoMesStr"] = df["Data emplacamento"].dt.strftime("%Y-%m") # Para exibição

        # Remover linhas onde datas ou colunas essenciais são inválidas
        df.dropna(subset=["Data emplacamento", "Ano", "Marca", "Segmento", "NO_CIDADE"], inplace=True)
        df["Ano"] = df["Ano"].astype(int)

        return df
    except FileNotFoundError:
        st.error(f"Erro: Arquivo Excel padrão não encontrado em {DEFAULT_EXCEL_FILE}. Faça o upload de um arquivo.")
        return None
    except Exception as e:
        file_info = "arquivo carregado" if isinstance(file_path_or_buffer, BytesIO) else os.path.basename(str(file_path_or_buffer))
        st.error(f"Erro ao carregar ou processar o arquivo Excel ({file_info}): {e}")
        return None

# --- Funções Auxiliares ---
def get_modes(series):
    cleaned_series = series.dropna().astype(str)
    if cleaned_series.empty:
        return ["N/A"]
    counts = Counter(cleaned_series)
    if not counts:
        return ["N/A"]
    max_count = counts.most_common(1)[0][1]
    modes = sorted([item for item, count in counts.items() if count == max_count])
    return modes

def format_list(items):
    if not items or items == ["N/A"]:
        return "N/A"
    return ", ".join(map(str, items))

def calculate_next_purchase_prediction(valid_purchase_dates):
    if not valid_purchase_dates or len(valid_purchase_dates) < 2:
        return "Previsão não disponível (histórico insuficiente).", None

    valid_purchase_dates.sort()
    last_purchase_date = valid_purchase_dates[-1]
    intervals_months = []
    for i in range(1, len(valid_purchase_dates)):
        delta = relativedelta(valid_purchase_dates[i], valid_purchase_dates[i-1])
        months_diff = delta.years * 12 + delta.months
        days_diff = delta.days
        if months_diff > 0:
            intervals_months.append(months_diff)
        elif months_diff == 0 and days_diff > 0:
             intervals_months.append(0.5)

    if not intervals_months:
         return "Previsão não disponível (compras muito próximas ou única).", last_purchase_date

    avg_interval_months = sum(intervals_months) / len(intervals_months)
    if avg_interval_months < 1:
        avg_interval_months = 1

    predicted_next_date = last_purchase_date + relativedelta(months=int(round(avg_interval_months)))

    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    predicted_month_year = f"{meses[predicted_next_date.month - 1]} de {predicted_next_date.year}"
    prediction_text = f"Próxima compra provável em: **{predicted_month_year}**"

    return prediction_text, predicted_next_date

def get_sales_pitch(last_purchase_date, predicted_next_date, total_purchases):
    today = pd.Timestamp.now().normalize()
    if not last_purchase_date:
        return "Primeira vez? 🤔 Sem histórico de compras registrado para este cliente."

    if not isinstance(last_purchase_date, pd.Timestamp):
        last_purchase_date = pd.to_datetime(last_purchase_date)

    months_since_last = relativedelta(today, last_purchase_date).years * 12 + relativedelta(today, last_purchase_date).months
    last_purchase_str = last_purchase_date.strftime("%d/%m/%Y")

    if predicted_next_date and isinstance(predicted_next_date, pd.Timestamp):
        months_to_next = relativedelta(predicted_next_date, today).years * 12 + relativedelta(predicted_next_date, today).months
        days_to_next = relativedelta(predicted_next_date, today).days
        predicted_month_year = f"{["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][predicted_next_date.month - 1]} de {predicted_next_date.year}"

        if months_to_next < 0 or (months_to_next == 0 and days_to_next < 0):
            return f"🚨 **Atenção!** A compra prevista para **{predicted_month_year}** pode estar próxima ou já passou! Última compra em {last_purchase_str}. Contato urgente!"
        elif months_to_next <= 2:
            return f"📈 **Oportunidade Quente!** Próxima compra prevista para **{predicted_month_year}**. Ótimo momento para contato! Última compra em {last_purchase_str}."
        elif months_to_next <= 6:
            return f"🗓️ **Planeje-se!** Próxima compra prevista para **{predicted_month_year}**. Prepare sua abordagem! Última compra em {last_purchase_str}."
        else:
            return f"⏳ Compra prevista para **{predicted_month_year}**. Mantenha o relacionamento aquecido! Última compra em {last_purchase_str}."
    else:
        if months_since_last >= 18:
            return f"🚨 Alerta de sumiço! Faz {months_since_last} meses desde a última compra ({last_purchase_str}). Hora de reativar esse cliente! 📞"
        elif months_since_last >= 12:
            return f"👀 E aí, sumido! Faz {months_since_last} meses desde a última compra ({last_purchase_str}). Que tal um alô para esse cliente?"
        elif months_since_last >= 6:
            return f"⏳ Já se passaram {months_since_last} meses... ({last_purchase_str}). Bom momento para um follow-up e mostrar as novidades!"
        elif total_purchases > 3:
             return f"👍 Cliente fiel ({total_purchases} compras)! Última compra em {last_purchase_str}. Mantenha o bom trabalho!"
        else:
            return f"✅ Compra recente ({last_purchase_str}). Ótimo para fortalecer o relacionamento!"

# --- Interface Principal --- 

# --- Cabeçalho ---
col1_header, col2_header = st.columns([1, 3])
with col1_header:
    if os.path.exists(LOGO_COLOR_PATH):
        st.image(LOGO_COLOR_PATH, width=250)
    else:
        st.warning("Logo colorido não encontrado.")
with col2_header:
    st.title("Consulta de Emplacamentos - VANS")
    st.markdown("**Ferramenta interna De Nigris** - Busque por cliente ou veja o resumo geral.")

st.divider()

# --- Upload e Carregamento de Dados (NOVA LÓGICA DE PERSISTÊNCIA) ---
st.sidebar.header("Atualizar Dados")
uploaded_file = st.sidebar.file_uploader("Selecione o arquivo Excel (.xlsx)", type=["xlsx"], key="file_uploader")

# Inicializar estado da sessão
if "dataframe" not in st.session_state:
    st.session_state["dataframe"] = None
if "data_source_info" not in st.session_state: # Armazena info sobre a fonte (nome do arquivo ou 'default')
    st.session_state["data_source_info"] = None
if "uploaded_file_content" not in st.session_state: # Armazena o CONTEÚDO do arquivo carregado
    st.session_state["uploaded_file_content"] = None

needs_reload = False
data_to_process = None
current_source_info = None

# 1. Verificar se um NOVO arquivo foi carregado
if uploaded_file is not None:
    uploaded_content = BytesIO(uploaded_file.getvalue())
    uploaded_info = f"uploaded_{uploaded_file.name}_{uploaded_file.size}"
    
    if uploaded_info != st.session_state.get("data_source_info"):
        st.session_state["uploaded_file_content"] = uploaded_content
        st.session_state["data_source_info"] = uploaded_info
        data_to_process = st.session_state["uploaded_file_content"]
        needs_reload = True
        st.sidebar.success(f"Arquivo 	'{uploaded_file.name}'	 pronto para carregar.")
    else:
        data_to_process = st.session_state["uploaded_file_content"]
        current_source_info = st.session_state["data_source_info"]
        if st.session_state.get("dataframe") is None:
            needs_reload = True

# 2. Se nenhum arquivo foi carregado, decidir qual usar
else:
    if st.session_state.get("uploaded_file_content") is not None:
        data_to_process = st.session_state["uploaded_file_content"]
        current_source_info = st.session_state["data_source_info"]
        if st.session_state.get("dataframe") is None:
            needs_reload = True
            st.sidebar.info("Usando arquivo carregado anteriormente.")
    elif os.path.exists(DEFAULT_EXCEL_FILE):
        data_to_process = DEFAULT_EXCEL_FILE
        current_source_info = "default"
        if st.session_state.get("data_source_info") != "default":
            st.session_state["uploaded_file_content"] = None
            st.session_state["data_source_info"] = "default"
            needs_reload = True
            st.sidebar.info(f"Usando arquivo padrão: {os.path.basename(DEFAULT_EXCEL_FILE)}")
        elif st.session_state.get("dataframe") is None:
             needs_reload = True
             st.sidebar.info(f"Usando arquivo padrão: {os.path.basename(DEFAULT_EXCEL_FILE)}")
    else:
        st.error("Nenhum arquivo de dados disponível. Faça o upload de um arquivo Excel ou certifique-se que o arquivo padrão existe.")
        st.stop()

# 3. Carregar os dados se necessário
if needs_reload and data_to_process is not None:
    # Rebobinar o BytesIO antes de ler novamente
    if isinstance(data_to_process, BytesIO):
        data_to_process.seek(0)
    st.session_state["dataframe"] = load_data(data_to_process)
    if st.session_state["dataframe"] is not None:
        st.sidebar.success("Dados carregados/atualizados!")
        st.rerun() # Força o rerender para UI refletir a mudança
    else:
        st.sidebar.error("Falha ao carregar/atualizar dados.")
        st.session_state["dataframe"] = None
        st.session_state["data_source_info"] = None
        st.session_state["uploaded_file_content"] = None

# Usar o dataframe do estado da sessão
df_full = st.session_state.get("dataframe")

if df_full is None or df_full.empty:
    st.warning("Os dados não puderam ser carregados ou estão vazios. Verifique o arquivo ou a mensagem de erro acima.")
    st.stop()

# --- Barra de Busca e Filtros --- 
st.subheader("Buscar Cliente Específico")
search_query = st.text_input("Digite o Nome ou CNPJ do cliente:", "", key="search_input")
search_button = st.button("Buscar", key="search_button")

st.sidebar.header("Filtros Gerais (Afetam Busca e Resumo)")
all_brands = sorted(df_full["Marca"].dropna().unique())
selected_brands = st.sidebar.multiselect("Filtrar por Marca:", all_brands)

all_segments = sorted(df_full["Segmento"].dropna().unique())
selected_segments = st.sidebar.multiselect("Filtrar por Segmento:", all_segments)

# Aplicar filtros ao DataFrame principal ANTES de qualquer cálculo
df_display = df_full.copy()
if selected_brands:
    df_display = df_display[df_display["Marca"].isin(selected_brands)]
if selected_segments:
    df_display = df_display[df_display["Segmento"].isin(selected_segments)]

# --- Exibição dos Resultados da Busca --- 
st.divider()

if search_button and search_query:
    st.markdown(f"### Resultados da Busca por: '{search_query}'")
    query_normalized = ''.join(filter(str.isdigit, str(search_query)))

    mask = (
        df_display["NOME DO CLIENTE"].str.contains(search_query, case=False, na=False)
    )
    if query_normalized and len(query_normalized) > 5:
         mask = mask | df_display["CNPJ_NORMALIZED"].str.contains(query_normalized, case=False, na=False)

    results_df = df_display[mask]

    if results_df.empty:
        st.warning("Cliente não encontrado na base de dados (considerando os filtros aplicados, se houver).")
    else:
        unique_cnpjs = results_df["CNPJ_NORMALIZED"].unique()

        if len(unique_cnpjs) > 1:
            st.info(f"Múltiplos clientes encontrados para \"{search_query}\". Exibindo o primeiro encontrado: {results_df.iloc[0]['NOME DO CLIENTE']} ({results_df.iloc[0]['CNPJ CLIENTE']}).")
            target_cnpj_normalized = unique_cnpjs[0]
        elif len(unique_cnpjs) == 1:
            target_cnpj_normalized = unique_cnpjs[0]
        else:
             st.warning("Não foi possível identificar um CNPJ único para o cliente.")
             st.stop()

        client_df = results_df[results_df["CNPJ_NORMALIZED"] == target_cnpj_normalized].copy()

        if not client_df.empty:
            client_df_sorted = client_df.sort_values(by="Data emplacamento", ascending=False)
            latest_record = client_df_sorted.iloc[0]

            client_name = latest_record["NOME DO CLIENTE"]
            client_cnpj_formatted = latest_record["CNPJ CLIENTE"]
            city_str = latest_record["NO_CIDADE"] if "NO_CIDADE" in latest_record and pd.notna(latest_record["NO_CIDADE"]) else "N/A"
            client_address = latest_record[NOME_COLUNA_ENDERECO]
            client_phone = latest_record[NOME_COLUNA_TELEFONE]

            total_plated = len(client_df)
            last_plate_date_obj = client_df["Data emplacamento"].dropna().max()
            last_plate_date_str = last_plate_date_obj.strftime("%d/%m/%Y") if pd.notna(last_plate_date_obj) else "N/A"
            most_frequent_model = get_modes(client_df["Modelo"])
            most_frequent_brand = get_modes(client_df["Marca"])
            most_frequent_segment = get_modes(client_df["Segmento"])
            most_frequent_dealer = get_modes(client_df["Concessionário"])

            st.markdown(f"#### Detalhes de: {client_name}")

            col1_info, col2_info = st.columns(2)
            with col1_info:
                st.markdown(f'<div class="info-card"><span class="label">Nome do Cliente:</span><span class="value">{client_name}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-card"><span class="label">CNPJ:</span><span class="value">{client_cnpj_formatted}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-card"><span class="label">Endereço:</span><span class="value">{client_address}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-card"><span class="label">Modelo(s) Mais Comprado(s):</span><span class="value">{format_list(most_frequent_model)}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-card"><span class="label">Concessionária(s) Mais Frequente(s):</span><span class="value">{format_list(most_frequent_dealer)}</span></div>', unsafe_allow_html=True)

            with col2_info:
                st.markdown(f'<div class="info-card"><span class="label">Cidade:</span><span class="value">{city_str}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-card"><span class="label">Telefone:</span><span class="value">{client_phone}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-card"><span class="label">Total Emplacado (na base):</span><span class="value">{total_plated}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-card"><span class="label">Último Emplacamento:</span><span class="value">{last_plate_date_str}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-card"><span class="label">Marca(s) Mais Comprada(s):</span><span class="value">{format_list(most_frequent_brand)}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-card"><span class="label">Segmento(s) Mais Comprado(s):</span><span class="value">{format_list(most_frequent_segment)}</span></div>', unsafe_allow_html=True)

            st.divider()

            # --- Previsão e Insight (MOVENDO PARA CIMA DO GRÁFICO) ---
            st.markdown("#### Previsão e Insight de Vendas")
            valid_dates = client_df["Data emplacamento"].dropna().tolist()
            prediction_text, predicted_date_obj = calculate_next_purchase_prediction(valid_dates)
            sales_pitch = get_sales_pitch(last_plate_date_obj, predicted_date_obj, total_plated)
            
            col_pred, col_insight = st.columns(2)
            with col_pred:
                st.info(prediction_text)
            with col_insight:
                st.success(f"💡 {sales_pitch}")
                
            st.markdown("#### Histórico de Compras")
            # Preparar dados para o gráfico
            client_df['AnoMesStr'] = client_df['Data emplacamento'].dt.strftime("%Y-%m") # Usar string para eixo X
            purchase_history = client_df.groupby('AnoMesStr').size().reset_index(name='Quantidade')
            # purchase_history['AnoMesStr'] = purchase_history['AnoMesStr'].astype(str) # Já é string

            if not purchase_history.empty:
                fig = px.bar(purchase_history, x='AnoMesStr', y='Quantidade', title=f'Histórico de Compras de {client_name}',
                             labels={'AnoMesStr': 'Mês/Ano', 'Quantidade': 'Nº de Emplacamentos'},
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(xaxis_title="Período", yaxis_title="Quantidade Emplacada")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Não há histórico de compras suficiente para gerar gráfico.")
        else:
            st.warning("Cliente encontrado, mas sem registros de emplacamento válidos.")
elif search_button and not search_query:
    st.warning("Por favor, digite um nome ou CNPJ para buscar.")
else:
    # --- RESUMO GERAL E ANÁLISES DE MERCADO (SE NENHUMA BUSCA FOI FEITA) --- 
    st.divider()
    st.subheader("Resumo Geral e Análise de Mercado - VANS (Considerando Filtros)")

    # Calcular estatísticas gerais do df_display (DataFrame filtrado)
    total_emplacamentos_display = len(df_display)
    total_clientes_unicos_display = df_display["CNPJ_NORMALIZED"].nunique()
    
    if not df_display.empty:
        primeiro_ano_display = int(df_display["Ano"].min())
        ultimo_ano_display = int(df_display["Ano"].max())
    else:
        primeiro_ano_display = "N/A"
        ultimo_ano_display = "N/A"

    col_resumo1, col_resumo2, col_resumo3 = st.columns(3)
    with col_resumo1:
        st.metric(label="Total de Emplacamentos (Filtro)", value=f"{total_emplacamentos_display:,}".replace(",", "."))
    with col_resumo2:
        st.metric(label="Total de Clientes Únicos (Filtro)", value=f"{total_clientes_unicos_display:,}".replace(",", "."))
    with col_resumo3:
        st.metric(label="Período Coberto (Filtro)", value=f"{primeiro_ano_display} - {ultimo_ano_display}")

    st.divider()
    st.markdown("#### Análises de Mercado (VANS)")

    if not df_display.empty:
        # 1. Tendências Gerais (por Mês/Ano)
        st.markdown("##### 1. Tendência Geral de Emplacamentos (Mês/Ano)")
        tendencia_mes_ano = df_display.groupby('AnoMesStr').size().reset_index(name='Quantidade')
        tendencia_mes_ano = tendencia_mes_ano.sort_values('AnoMesStr') # Ordenar por data
        if not tendencia_mes_ano.empty:
            fig_tendencia = px.line(tendencia_mes_ano, x='AnoMesStr', y='Quantidade', 
                                    title="Emplacamentos de VANS ao Longo do Tempo",
                                    labels={'AnoMesStr': 'Mês/Ano', 'Quantidade': 'Nº de Emplacamentos'})
            fig_tendencia.update_layout(xaxis_title="Período", yaxis_title="Quantidade Emplacada")
            st.plotly_chart(fig_tendencia, use_container_width=True)
        else:
            st.info("Não há dados suficientes para exibir a tendência mensal.")

        # 2. Market Share por Marca
        st.markdown("##### 2. Market Share por Marca")
        market_share_marca = df_display['Marca'].value_counts().reset_index(name='Quantidade')
        market_share_marca.columns = ['Marca', 'Quantidade']
        if not market_share_marca.empty:
            fig_share = px.pie(market_share_marca, names='Marca', values='Quantidade', 
                               title="Participação de Mercado por Marca de VAN",
                               hole=0.3) # Gráfico de rosca
            fig_share.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_share, use_container_width=True)
        else:
            st.info("Não há dados suficientes para exibir o market share por marca.")

        # 3. Distribuição Geográfica por Cidade (Tabela Top 15)
        st.markdown("##### 3. Distribuição Geográfica (Top 15 Cidades)")
        dist_cidade = df_display['NO_CIDADE'].value_counts().reset_index(name='Quantidade')
        dist_cidade.columns = ['Cidade', 'Quantidade']
        if not dist_cidade.empty:
            st.dataframe(dist_cidade.head(15), use_container_width=True)
        else:
            st.info("Não há dados suficientes para exibir a distribuição por cidade.")

        # 4. Análise por Segmento
        st.markdown("##### 4. Análise por Segmento")
        analise_segmento = df_display['Segmento'].value_counts().reset_index(name='Quantidade')
        analise_segmento.columns = ['Segmento', 'Quantidade']
        if not analise_segmento.empty:
            fig_segmento = px.bar(analise_segmento, x='Segmento', y='Quantidade', 
                                  title="Emplacamentos por Segmento de VAN",
                                  labels={'Segmento': 'Segmento', 'Quantidade': 'Nº de Emplacamentos'},
                                  color='Segmento')
            st.plotly_chart(fig_segmento, use_container_width=True)
        else:
            st.info("Não há dados suficientes para exibir a análise por segmento.")

    else:
        st.info("Não há dados para exibir as análises de mercado com os filtros aplicados.")

# --- Rodapé (Opcional) ---
st.sidebar.divider()
if os.path.exists(LOGO_WHITE_PATH):
    st.sidebar.image(LOGO_WHITE_PATH, use_container_width=True)
else:
    st.sidebar.warning("Logo branco não encontrado.")
st.sidebar.caption("© De Nigris Distribuidora")

