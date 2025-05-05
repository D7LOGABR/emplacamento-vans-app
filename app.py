import streamlit as st
import pandas as pd
import plotly.express as px
from dateutil.relativedelta import relativedelta
from collections import Counter
import os
import numpy as np
from io import BytesIO

# --- Configuração da Página ---
st.set_page_config(
    page_title="Emplacamentos VANS De Nigris",
    page_icon="🚚",
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
# Certifique-se que estes nomes correspondem EXATAMENTE aos da sua planilha
NOME_COLUNA_ENDERECO = "ENDEREÇO COMPLETO"
NOME_COLUNA_TELEFONE = "TELEFONE1" # <--- IMPORTANTE: Verifique e ajuste se necessário!

# --- Funções de Carregamento de Dados ---
@st.cache_data(ttl=3600) # Cache por 1 hora para evitar recarregamentos constantes
def load_data(file_path_or_buffer):
    """Carrega e pré-processa os dados do arquivo Excel."""
    try:
        df = pd.read_excel(file_path_or_buffer)

        # Verificar se o DataFrame está vazio
        if df.empty:
            st.error("O arquivo Excel não contém dados.")
            return None

        # Garantir que colunas essenciais para análise existam
        essential_cols = ["Marca", "Segmento", "NO_CIDADE", "Data emplacamento", "CNPJ CLIENTE", "NOME DO CLIENTE"]
        missing_cols = [col for col in essential_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Erro: Colunas essenciais não encontradas no arquivo Excel: {", ".join(missing_cols)}")
            return None

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

        # Normalizar CNPJ
        df["CNPJ_NORMALIZED"] = df["CNPJ CLIENTE"].str.replace(r"[.\\/-]", "", regex=True)
        
        # Remover linhas onde datas ou colunas essenciais são inválidas
        # Primeiro, remover linhas com data de emplacamento inválida
        df = df.dropna(subset=["Data emplacamento"])
        
        # Extrair ano e mês com tratamento seguro para NaN
        df["Ano"] = df["Data emplacamento"].dt.year
        df["Mes"] = df["Data emplacamento"].dt.month
        
        # Tratar valores NaN em Ano e Mes antes de converter para int
        # Remover linhas com Ano ou Mes inválidos
        df = df.dropna(subset=["Ano", "Mes"])
        
        # Converter para int com segurança
        df["Ano"] = df["Ano"].astype(int)
        df["Mes"] = df["Mes"].astype(int)
        
        # Criar AnoMesStr com segurança (apenas para linhas com data válida)
        df["AnoMesStr"] = df["Data emplacamento"].dt.strftime("%Y-%m")
        
        # Criar AnoMesNum com segurança
        # Primeiro criar uma string temporária e depois converter para int
        df["AnoMesTemp"] = df["Ano"].astype(str) + df["Mes"].apply(lambda x: f"{x:02d}")
        df["AnoMesNum"] = df["AnoMesTemp"].astype(int)
        df = df.drop(columns=["AnoMesTemp"])  # Remover coluna temporária
        
        # Remover linhas onde outras colunas essenciais são inválidas
        df = df.dropna(subset=["Marca", "Segmento", "NO_CIDADE", "CNPJ CLIENTE", "NOME DO CLIENTE"])
        
        # Verificar se ainda temos dados após a limpeza
        if df.empty:
            st.error("Após remover linhas com dados inválidos, não restaram registros para análise.")
            return None
            
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
        # Considerar intervalo mínimo de 1 mês, mesmo que dias sejam > 0
        if months_diff > 0:
            intervals_months.append(months_diff)
        elif months_diff == 0 and days_diff > 15: # Se mais de 15 dias, conta como ~0.5 mês
             intervals_months.append(0.5)
        # Ignorar intervalos muito curtos (menos de 15 dias)

    if not intervals_months:
         return "Previsão não disponível (compras muito próximas ou única).", last_purchase_date

    avg_interval_months = sum(intervals_months) / len(intervals_months)
    # Definir um intervalo mínimo razoável (ex: 1 mês)
    avg_interval_months = max(1, avg_interval_months)

    predicted_next_date = last_purchase_date + relativedelta(months=int(round(avg_interval_months)))

    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    predicted_month_year = f"{meses[predicted_next_date.month - 1]} de {predicted_next_date.year}"
    prediction_text = f"Próxima compra provável em: **{predicted_month_year}** (intervalo médio: {avg_interval_months:.1f} meses)"

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

        if months_to_next < 0 or (months_to_next == 0 and days_to_next < -7): # Já passou há mais de uma semana
            return f"🚨 **Atenção!** A compra prevista para **{predicted_month_year}** pode ter passado! Última compra em {last_purchase_str}. Contato urgente!"
        elif months_to_next <= 1 and days_to_next >= -7: # Próximo mês ou já passou há poucos dias
            return f"📈 **Oportunidade Quente!** Próxima compra prevista para **{predicted_month_year}**. Ótimo momento para contato! Última compra em {last_purchase_str}."
        elif months_to_next <= 3:
            return f"🗓️ **Planeje-se!** Próxima compra prevista para **{predicted_month_year}**. Prepare sua abordagem! Última compra em {last_purchase_str}."
        else:
            return f"⏳ Compra prevista para **{predicted_month_year}**. Mantenha o relacionamento aquecido! Última compra em {last_purchase_str}."
    else:
        # Sem previsão, usar tempo desde a última compra
        if months_since_last >= 18:
            return f"🚨 Alerta de inatividade! Faz {months_since_last} meses desde a última compra ({last_purchase_str}). Hora de reativar esse cliente! 📞"
        elif months_since_last >= 12:
            return f"👀 Faz {months_since_last} meses desde a última compra ({last_purchase_str}). Que tal um contato para mostrar novidades?"
        elif months_since_last >= 6:
            return f"⏳ Já se passaram {months_since_last} meses ({last_purchase_str}). Bom momento para um follow-up."
        elif total_purchases > 3:
             return f"👍 Cliente fiel ({total_purchases} compras)! Última compra em {last_purchase_str}. Mantenha o bom trabalho!"
        else:
            return f"✅ Compra recente ({last_purchase_str}). Ótimo para fortalecer o relacionamento!"

# --- Gerenciamento de Estado e Carregamento de Dados ---

# Inicializar estado da sessão se necessário
if "df_loaded" not in st.session_state:
    st.session_state.df_loaded = None # Armazena o DataFrame carregado
if "data_source_key" not in st.session_state:
    st.session_state.data_source_key = None # Chave para identificar a fonte (default ou upload)
if "last_upload_info" not in st.session_state:
    st.session_state.last_upload_info = None # Guarda nome e tamanho do último upload

st.sidebar.header("Atualizar Dados")
uploaded_file = st.sidebar.file_uploader("Selecione o arquivo Excel (.xlsx)", type=["xlsx"], key="file_uploader")

load_from_default = False
load_from_upload = False

# Lógica de decisão para carregar/recarregar dados
if uploaded_file is not None:
    # Novo upload detectado
    current_upload_info = (uploaded_file.name, uploaded_file.size)
    if current_upload_info != st.session_state.last_upload_info:
        # É um arquivo diferente do último upload ou o primeiro upload
        load_from_upload = True
        st.session_state.last_upload_info = current_upload_info
        st.sidebar.info(f"Arquivo 	'{uploaded_file.name}'	 selecionado.")
    elif st.session_state.df_loaded is None:
        # Mesmo arquivo, mas DataFrame não está carregado (ex: após erro)
        load_from_upload = True
elif st.session_state.df_loaded is None:
    # Nenhum upload ativo e nenhum DataFrame carregado, tentar carregar do default
    load_from_default = True

# Executar o carregamento se necessário
data_loaded_successfully = False
if load_from_upload:
    try:
        uploaded_content = BytesIO(uploaded_file.getvalue())
        st.session_state.df_loaded = load_data(uploaded_content)
        if st.session_state.df_loaded is not None:
            st.session_state.data_source_key = f"upload_{uploaded_file.name}_{uploaded_file.size}"
            st.sidebar.success("Dados do arquivo carregado!")
            data_loaded_successfully = True
            st.rerun() # Força recarregar a UI com os novos dados
        else:
            st.session_state.data_source_key = None # Falha no carregamento
            st.session_state.last_upload_info = None # Resetar info do upload
    except Exception as e:
        st.sidebar.error(f"Erro ao processar upload: {e}")
        st.session_state.df_loaded = None
        st.session_state.data_source_key = None
        st.session_state.last_upload_info = None

elif load_from_default:
    if os.path.exists(DEFAULT_EXCEL_FILE):
        try:
            st.session_state.df_loaded = load_data(DEFAULT_EXCEL_FILE)
            if st.session_state.df_loaded is not None:
                st.session_state.data_source_key = "default"
                st.sidebar.info(f"Usando arquivo padrão: {os.path.basename(DEFAULT_EXCEL_FILE)}")
                data_loaded_successfully = True
                # Não precisa de rerun aqui, pois é o carregamento inicial
            else:
                st.session_state.data_source_key = None # Falha no carregamento
        except Exception as e:
            st.sidebar.error(f"Erro ao carregar arquivo padrão: {e}")
            st.session_state.df_loaded = None
            st.session_state.data_source_key = None
    else:
        st.sidebar.warning(f"Arquivo padrão não encontrado em {DEFAULT_EXCEL_FILE}. Faça upload de um arquivo.")
        st.session_state.df_loaded = None
        st.session_state.data_source_key = None

# Verificar se temos um DataFrame para trabalhar
df_full = st.session_state.get("df_loaded")

if df_full is None or df_full.empty:
    st.warning("Nenhum dado carregado. Faça o upload de um arquivo Excel ou verifique o arquivo padrão.")
    st.stop() # Interrompe a execução se não houver dados

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

# --- Barra de Busca e Filtros (MOVIMENTADO PARA CIMA) --- 
st.subheader("Buscar Cliente Específico")
search_query = st.text_input("Digite o Nome ou CNPJ do cliente:", "", key="search_input")
search_button = st.button("Buscar", key="search_button")

st.sidebar.header("Filtros Gerais (Afetam Busca e Resumo)")
all_brands = sorted(df_full["Marca"].dropna().unique())
selected_brands = st.sidebar.multiselect("Filtrar por Marca:", all_brands, key="brand_filter")

all_segments = sorted(df_full["Segmento"].dropna().unique())
selected_segments = st.sidebar.multiselect("Filtrar por Segmento:", all_segments, key="segment_filter")

# Aplicar filtros ao DataFrame principal ANTES de qualquer cálculo
df_display = df_full.copy()
if selected_brands:
    df_display = df_display[df_display["Marca"].isin(selected_brands)]
if selected_segments:
    df_display = df_display[df_display["Segmento"].isin(selected_segments)]

# --- Exibição dos Resultados da Busca ou Resumo Geral --- 
st.divider()

if search_button and search_query:
    # --- Resultados da Busca Específica ---
    st.markdown(f"### Resultados da Busca por: 	'{search_query}'")
    query_normalized = 	''.join(filter(str.isdigit, str(search_query)))

    mask = (
        df_display["NOME DO CLIENTE"].str.contains(search_query, case=False, na=False)
    )
    # Só busca por CNPJ normalizado se a query tiver dígitos
    if query_normalized:
         mask = mask | df_display["CNPJ_NORMALIZED"].str.contains(query_normalized, case=False, na=False)

    results_df = df_display[mask]

    if results_df.empty:
        st.warning("Cliente não encontrado na base de dados (considerando os filtros aplicados, se houver).")
    else:
        unique_cnpjs = results_df["CNPJ_NORMALIZED"].unique()

        if len(unique_cnpjs) > 1:
            # Se múltiplos CNPJs, pegar o primeiro como referência (pode precisar de lógica mais sofisticada)
            target_cnpj_normalized = unique_cnpjs[0]
            first_match_name = results_df[results_df["CNPJ_NORMALIZED"] == target_cnpj_normalized]["NOME DO CLIENTE"].iloc[0]
            first_match_cnpj = results_df[results_df["CNPJ_NORMALIZED"] == target_cnpj_normalized]["CNPJ CLIENTE"].iloc[0]
            st.info(f"Múltiplos clientes encontrados para \"{search_query}\". Exibindo resultados para: **{first_match_name} ({first_match_cnpj})**.")
        elif len(unique_cnpjs) == 1:
            target_cnpj_normalized = unique_cnpjs[0]
        else:
             # Caso estranho: máscara funcionou mas não achou CNPJ (não deveria acontecer com dropna)
             st.warning("Não foi possível identificar um CNPJ único para o cliente.")
             st.stop()

        # Filtrar DataFrame para o CNPJ alvo
        client_df = df_display[df_display["CNPJ_NORMALIZED"] == target_cnpj_normalized].copy()

        if not client_df.empty:
            client_df_sorted = client_df.sort_values(by="Data emplacamento", ascending=False)
            latest_record = client_df_sorted.iloc[0]

            # Informações básicas do cliente
            client_name = latest_record["NOME DO CLIENTE"]
            client_cnpj_formatted = latest_record["CNPJ CLIENTE"]
            client_address = latest_record.get(NOME_COLUNA_ENDERECO, "N/A")
            client_phone = latest_record.get(NOME_COLUNA_TELEFONE, "N/A")
            client_city = latest_record.get("NO_CIDADE", "N/A")

            st.subheader(f"Detalhes de: {client_name}")
            col1_info, col2_info = st.columns(2)
            with col1_info:
                st.markdown(f"<div class='info-card'><span class='label'>CNPJ:</span><span class='value'>{client_cnpj_formatted}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='info-card'><span class='label'>Endereço:</span><span class='value'>{client_address}</span></div>", unsafe_allow_html=True)
            with col2_info:
                st.markdown(f"<div class='info-card'><span class='label'>Cidade:</span><span class='value'>{client_city}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='info-card'><span class='label'>Telefone:</span><span class='value'>{client_phone}</span></div>", unsafe_allow_html=True)

            st.markdown("#### Análise e Histórico")

            # Cálculos para análise
            total_purchases = len(client_df_sorted)
            first_purchase_date = client_df_sorted["Data emplacamento"].min()
            last_purchase_date = client_df_sorted["Data emplacamento"].max()
            valid_purchase_dates = client_df_sorted["Data emplacamento"].dropna().tolist()

            # Calcular previsão e pitch
            prediction_text, predicted_next_date = calculate_next_purchase_prediction(valid_purchase_dates)
            sales_pitch = get_sales_pitch(last_purchase_date, predicted_next_date, total_purchases)

            # Exibir Insight e Previsão (MOVIMENTADO PARA CIMA)
            col1_insight, col2_predict = st.columns(2)
            with col1_insight:
                 st.markdown(f"**Insight de Vendas:**")
                 st.info(sales_pitch)
            with col2_predict:
                 st.markdown(f"**Previsão de Próxima Compra:**")
                 st.info(prediction_text)

            # Métricas Resumidas do Cliente
            col1_metric, col2_metric, col3_metric = st.columns(3)
            col1_metric.metric("Total de Emplacamentos", total_purchases)
            col2_metric.metric("Primeira Compra", first_purchase_date.strftime("%d/%m/%Y") if pd.notna(first_purchase_date) else "N/A")
            col3_metric.metric("Última Compra", last_purchase_date.strftime("%d/%m/%Y") if pd.notna(last_purchase_date) else "N/A")

            # Histórico de Compras
            st.markdown("##### Histórico de Emplacamentos")
            client_df_display = client_df_sorted[["Data emplacamento", "Marca", "Modelo", "Segmento"]].rename(columns={
                "Data emplacamento": "Data",
                "Marca": "Marca",
                "Modelo": "Modelo",
                "Segmento": "Segmento"
            })
            client_df_display["Data"] = client_df_display["Data"].dt.strftime("%d/%m/%Y")
            st.dataframe(client_df_display, use_container_width=True)

            # Gráfico de Frequência de Compra
            if total_purchases > 1:
                st.markdown("##### Frequência de Compra (por Mês/Ano)")
                purchase_frequency = client_df_sorted.groupby("AnoMesStr").size().reset_index(name="Count")
                # Garantir que AnoMesNum existe e é int antes de ordenar
                if "AnoMesNum" in purchase_frequency.columns:
                    purchase_frequency["AnoMesNum"] = purchase_frequency["AnoMesNum"].astype(int)
                    purchase_frequency = purchase_frequency.sort_values("AnoMesNum")
                
                fig_freq = px.bar(purchase_frequency, x="AnoMesStr", y="Count", title="Emplacamentos ao Longo do Tempo", labels={'AnoMesStr': 'Mês/Ano', 'Count': 'Qtd. Emplacamentos'})
                fig_freq.update_layout(xaxis_title="", yaxis_title="Quantidade")
                st.plotly_chart(fig_freq, use_container_width=True)
            else:
                st.info("Gráfico de frequência não disponível (apenas uma compra registrada).")

            # Análise de Preferências
            st.markdown("##### Preferências do Cliente")
            pref_cols = st.columns(3)
            preferred_brands = get_modes(client_df["Marca"])
            preferred_segments = get_modes(client_df["Segmento"])
            preferred_models = get_modes(client_df["Modelo"])

            pref_cols[0].metric("Marca(s) Preferida(s)", format_list(preferred_brands))
            pref_cols[1].metric("Segmento(s) Preferido(s)", format_list(preferred_segments))
            pref_cols[2].metric("Modelo(s) Preferido(s)", format_list(preferred_models))

        else:
            # Isso não deve acontecer se results_df não estava vazio e o CNPJ foi identificado
            st.error("Erro inesperado ao filtrar os dados do cliente.")
else:
    # --- Resumo Geral (se nenhuma busca ativa) ---
    st.subheader("Resumo Geral da Base de Dados")
    st.markdown("*(Considerando os filtros aplicados na barra lateral, se houver)*")

    if df_display.empty:
        st.warning("Nenhum dado disponível para exibir com os filtros selecionados.")
    else:
        # Métricas Gerais
        total_emplacamentos = len(df_display)
        total_clientes = df_display["CNPJ_NORMALIZED"].nunique()
        data_inicio = df_display["Data emplacamento"].min()
        data_fim = df_display["Data emplacamento"].max()

        col1_res, col2_res, col3_res = st.columns(3)
        col1_res.metric("Total de Emplacamentos", total_emplacamentos)
        col2_res.metric("Clientes Únicos", total_clientes)
        col3_res.metric("Período Coberto", f"{data_inicio.strftime('%m/%Y') if pd.notna(data_inicio) else 'N/A'} a {data_fim.strftime('%m/%Y') if pd.notna(data_fim) else 'N/A'}")

        st.markdown("#### Emplacamentos por Ano")
        # Garantir que não há NaN em Ano antes de agrupar
        emplac_por_ano = df_display.dropna(subset=["Ano"]).groupby("Ano").size().reset_index(name="Count")
        if not emplac_por_ano.empty:
            emplac_por_ano["Ano"] = emplac_por_ano["Ano"].astype(int)  # Garantir que Ano é int
            fig_ano = px.bar(emplac_por_ano, x="Ano", y="Count", title="Total de Emplacamentos por Ano", labels={'Ano': 'Ano', 'Count': 'Quantidade'})
            fig_ano.update_layout(xaxis_type='category') # Tratar ano como categoria
            st.plotly_chart(fig_ano, use_container_width=True)
        else:
            st.info("Não há dados suficientes para gerar o gráfico de emplacamentos por ano.")

        st.markdown("#### Emplacamentos por Marca e Ano")
        # Garantir que não há NaN em Ano ou Marca antes de agrupar
        emplac_marca_ano = df_display.dropna(subset=["Ano", "Marca"]).groupby(["Ano", "Marca"]).size().reset_index(name="Count")
        if not emplac_marca_ano.empty:
            emplac_marca_ano["Ano"] = emplac_marca_ano["Ano"].astype(int)  # Garantir que Ano é int
            
            # Pivotar para formato wide
            try:
                pivot_marca_ano = emplac_marca_ano.pivot(index="Marca", columns="Ano", values="Count").fillna(0).astype(int)
                # Adicionar total por marca
                pivot_marca_ano["Total"] = pivot_marca_ano.sum(axis=1)
                # Ordenar pelo total
                pivot_marca_ano = pivot_marca_ano.sort_values("Total", ascending=False)
                st.dataframe(pivot_marca_ano, use_container_width=True)
            except Exception as pivot_error:
                st.warning(f"Não foi possível gerar a tabela de emplacamentos por marca e ano: {pivot_error}")
        else:
            st.info("Não há dados suficientes para gerar a tabela de emplacamentos por marca e ano.")

# --- Rodapé (Opcional) ---
st.sidebar.divider()
if os.path.exists(LOGO_WHITE_PATH):
    st.sidebar.image(LOGO_WHITE_PATH, width=150)
st.sidebar.markdown("© De Nigris Distribuidora")
