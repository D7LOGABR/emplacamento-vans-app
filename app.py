import streamlit as st
import pandas as pd
import plotly.express as px
from dateutil.relativedelta import relativedelta
from collections import Counter
import os
import numpy as np
from io import BytesIO

# =================== BLOQUEIO DE ACESSO ===================
SENHA_CORRETA = "23290000"

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("## 🔒 Acesso Restrito")
    st.markdown("Digite a senha para acessar o sistema.")

    senha_digitada = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if senha_digitada == SENHA_CORRETA:
            st.session_state.autenticado = True
            st.success("✅ Acesso liberado")
            st.rerun()
        else:
            st.error("❌ Senha incorreta")

    st.stop()
# =========================================================

st.set_page_config(
    page_title="Emplacamentos VANS De Nigris",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }
    .info-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 5px solid #0055a4;
    }
    .info-card .label {
        font-weight: bold;
        color: #003366;
        display: block;
        margin-bottom: 3px;
    }
    .info-card .value {
        color: #333;
    }
    h1, h2, h3, h4 {
        color: #003366;
    }
    .stButton>button {
        background-color: #0055a4;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
    }
    .stButton>button:hover {
        background-color: #003366;
        color: white;
    }
    .stAlert p {
        font-size: 1rem;
    }
    .stMetric {
        background-color: #e9ecef;
        border-radius: 8px;
        padding: 10px 15px;
        border-left: 5px solid #6c757d;
    }
</style>
""", unsafe_allow_html=True)

DATA_DIR = "data"
DEFAULT_EXCEL_FILE = os.path.join(DATA_DIR, "EMPLACAMENTO ANUAL - VANS.xlsx")
LOGO_COLOR_PATH = os.path.join(DATA_DIR, "logo_denigris_colorido.png")
LOGO_WHITE_PATH = os.path.join(DATA_DIR, "logo_denigris_branco.png")

NOME_COLUNA_ENDERECO = "ENDEREÇO COMPLETO"
NOME_COLUNA_TELEFONE = "TELEFONE1"
NOME_COLUNA_CONCESSIONARIO = "CONCESSIONÁRIO"

@st.cache_data(ttl=3600)
def load_data(file_path_or_buffer):
    try:
        df = pd.read_excel(file_path_or_buffer)
        if df.empty:
            st.error("O arquivo Excel não contém dados.")
            return None

        essential_cols = ["Marca", "Segmento", "NO_CIDADE", "Data emplacamento", "CNPJ CLIENTE", "NOME DO CLIENTE"]
        missing_cols = [col for col in essential_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Erro: Colunas essenciais não encontradas: {', '.join(missing_cols)}")
            return None

        placa_col = "PLACA"
        if placa_col in df.columns:
            df[placa_col] = df[placa_col].astype(str).str.strip().str.upper()
            df["PLACA_NORMALIZED"] = df[placa_col].str.replace("-", "").str.replace(" ", "").str.upper()
        else:
            df[placa_col] = ""
            df["PLACA_NORMALIZED"] = ""

        concessionario_variations = ["CONCESSIONÁRIO", "concessionário", "Concessionário", "Concessionaria", "CONCESSIONARIO"]
        found_concessionario_col = next((col for col in concessionario_variations if col in df.columns), None)
        if found_concessionario_col and found_concessionario_col != NOME_COLUNA_CONCESSIONARIO:
            df.rename(columns={found_concessionario_col: NOME_COLUNA_CONCESSIONARIO}, inplace=True)
        if NOME_COLUNA_CONCESSIONARIO not in df.columns:
            df[NOME_COLUNA_CONCESSIONARIO] = "N/A"

        df["Data emplacamento"] = pd.to_datetime(df["Data emplacamento"], errors='coerce', dayfirst=True)
        df["CNPJ CLIENTE"] = df["CNPJ CLIENTE"].astype(str).str.strip()
        df["NOME DO CLIENTE"] = df["NOME DO CLIENTE"].astype(str).str.strip()
        df[NOME_COLUNA_ENDERECO] = df[NOME_COLUNA_ENDERECO].astype(str).str.strip() if NOME_COLUNA_ENDERECO in df.columns else "N/A"
        df[NOME_COLUNA_TELEFONE] = df[NOME_COLUNA_TELEFONE].astype(str).str.strip() if NOME_COLUNA_TELEFONE in df.columns else "N/A"
        df[NOME_COLUNA_CONCESSIONARIO] = df[NOME_COLUNA_CONCESSIONARIO].astype(str).str.strip()
        df["CNPJ_NORMALIZED"] = df["CNPJ CLIENTE"].str.replace(r"[.\\/-]", "", regex=True)
        df.dropna(subset=["Data emplacamento", "CNPJ CLIENTE", "NOME DO CLIENTE"], inplace=True)
        df["Ano"] = df["Data emplacamento"].dt.year
        df["Mes"] = df["Data emplacamento"].dt.month
        df["AnoMesStr"] = df["Data emplacamento"].dt.strftime("%Y-%m")
        df["AnoMesNum"] = (df["Ano"] * 100 + df["Mes"]).astype(int)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar/processar o arquivo: {e}")
        return None
def get_modes(series):
    cleaned_series = series.dropna().astype(str)
    cleaned_series = cleaned_series[cleaned_series != "N/A"]
    cleaned_series = cleaned_series[cleaned_series != ""]
    if cleaned_series.empty:
        return ["N/A"]
    counts = Counter(cleaned_series)
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
        elif months_diff == 0 and days_diff > 15:
            intervals_months.append(0.5)
    if not intervals_months:
        return "Previsão não disponível (compras muito próximas ou única).", last_purchase_date
    avg_interval_months = max(1, sum(intervals_months) / len(intervals_months))
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
        predicted_month_year = f"{['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'][predicted_next_date.month - 1]} de {predicted_next_date.year}"
        if months_to_next < 0 or (months_to_next == 0 and days_to_next < -7):
            return f"🚨 **Atenção!** A compra prevista para **{predicted_month_year}** pode ter passado! Última compra em {last_purchase_str}. Contato urgente!"
        elif months_to_next <= 1 and days_to_next >= -7:
            return f"📈 **Oportunidade Quente!** Próxima compra prevista para **{predicted_month_year}**. Ótimo momento para contato! Última compra em {last_purchase_str}."
        elif months_to_next <= 3:
            return f"🗓️ **Planeje-se!** Próxima compra prevista para **{predicted_month_year}**. Prepare sua abordagem! Última compra em {last_purchase_str}."
        else:
            return f"⏳ Compra prevista para **{predicted_month_year}**. Mantenha o relacionamento aquecido! Última compra em {last_purchase_str}."
    else:
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

if "df_loaded" not in st.session_state:
    st.session_state.df_loaded = None
if "data_source_key" not in st.session_state:
    st.session_state.data_source_key = None
if "last_upload_info" not in st.session_state:
    st.session_state.last_upload_info = None

st.sidebar.header("Atualizar Dados")
uploaded_file = st.sidebar.file_uploader("Selecione o arquivo Excel (.xlsx)", type=["xlsx"], key="file_uploader")

load_from_default = False
load_from_upload = False

if uploaded_file is not None:
    current_upload_info = (uploaded_file.name, uploaded_file.size)
    if current_upload_info != st.session_state.last_upload_info:
        load_from_upload = True
        st.session_state.last_upload_info = current_upload_info
        st.sidebar.info(f"Arquivo 	'{uploaded_file.name}'	 selecionado.")
    elif st.session_state.df_loaded is None:
        load_from_upload = True
elif st.session_state.df_loaded is None:
    load_from_default = True

if load_from_upload:
    try:
        uploaded_content = BytesIO(uploaded_file.getvalue())
        st.session_state.df_loaded = load_data(uploaded_content)
        if st.session_state.df_loaded is not None:
            st.session_state.data_source_key = f"upload_{uploaded_file.name}_{uploaded_file.size}"
            st.sidebar.success("Dados do arquivo carregado!")
            st.rerun()
        else:
            st.session_state.data_source_key = None
            st.session_state.last_upload_info = None
    except Exception as e:
        st.sidebar.error(f"Erro crítico ao processar upload: {e}")
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
            else:
                st.session_state.data_source_key = None
        except Exception as e:
            st.sidebar.error(f"Erro crítico ao carregar arquivo padrão: {e}")
            st.session_state.df_loaded = None
            st.session_state.data_source_key = None
    else:
        st.sidebar.warning(f"Arquivo padrão não encontrado em {DEFAULT_EXCEL_FILE}. Faça upload de um arquivo.")
        st.session_state.df_loaded = None
        st.session_state.data_source_key = None

df_full = st.session_state.get("df_loaded")

if df_full is None or df_full.empty:
    st.warning("Os dados não puderam ser carregados ou estão vazios. Verifique o arquivo ou a mensagem de erro acima.")
    st.stop()

col1_header, col2_header = st.columns([1, 3])
with col1_header:
    if os.path.exists(LOGO_COLOR_PATH):
        st.image(LOGO_COLOR_PATH, width=250)
    else:
        st.warning("Logo colorido não encontrado.")
with col2_header:
    st.title("Consulta de Emplacamentos - VANS")
    st.markdown("**Ferramenta interna De Nigris** - Busque por cliente, placa ou CNPJ ou veja o resumo geral.")

st.divider()

st.subheader("Buscar Cliente, Placa ou CNPJ")
search_query = st.text_input("Digite o Nome, CNPJ ou Placa do cliente:", "", key="search_input")
search_button = st.button("Buscar", key="search_button")

st.sidebar.header("Filtros Gerais (Afetam Busca e Resumo)")
all_brands = sorted(df_full["Marca"].dropna().unique())
selected_brands = st.sidebar.multiselect("Filtrar por Marca:", all_brands, key="brand_filter")
all_segments = sorted(df_full["Segmento"].dropna().unique())
selected_segments = st.sidebar.multiselect("Filtrar por Segmento:", all_segments, key="segment_filter")

df_display = df_full.copy()
if selected_brands:
    df_display = df_display[df_display["Marca"].isin(selected_brands)]
if selected_segments:
    df_display = df_display[df_display["Segmento"].isin(selected_segments)]

st.divider()

if search_button and search_query:
    st.markdown(f"### Resultados da Busca por: '{search_query}'")
    query_placa_normalized = search_query.replace("-", "").replace(" ", "").upper()
    query_cnpj_normalized = ''.join(filter(str.isdigit, str(search_query)))

    # Busca exata por placa
    df_found = df_display[df_display["PLACA_NORMALIZED"] == query_placa_normalized]
    if df_found.empty and len(query_cnpj_normalized) >= 11:
        # Busca exata por CNPJ normalizado
        df_found = df_display[df_display["CNPJ_NORMALIZED"] == query_cnpj_normalized]
    if df_found.empty:
        # Busca por nome (parcial, case-insensitive)
        df_found = df_display[df_display["NOME DO CLIENTE"].str.contains(search_query, case=False, na=False)]

    if df_found.empty:
        st.warning("Cliente ou placa não encontrado na base de dados (considerando os filtros aplicados, se houver).")
    else:
        unique_cnpjs = df_found["CNPJ_NORMALIZED"].unique()
        if len(unique_cnpjs) > 1:
            cnpj_options = df_found.drop_duplicates('CNPJ_NORMALIZED')[["NOME DO CLIENTE", "CNPJ CLIENTE", "CNPJ_NORMALIZED"]]
            cnpj_labels = [f"{row['NOME DO CLIENTE']} ({row['CNPJ CLIENTE']})" for idx, row in cnpj_options.iterrows()]
            cnpj_selected = st.selectbox("Múltiplos clientes encontrados. Selecione o desejado:", options=cnpj_labels)
            idx_selected = cnpj_labels.index(cnpj_selected)
            cnpj_escolhido = cnpj_options.iloc[idx_selected]["CNPJ_NORMALIZED"]
            df_found = df_found[df_found["CNPJ_NORMALIZED"] == cnpj_escolhido]

        client_df_sorted = df_found.sort_values(by="Data emplacamento", ascending=False)
        latest_record = client_df_sorted.iloc[0]
        client_name = latest_record["NOME DO CLIENTE"]
        client_cnpj_formatted = latest_record["CNPJ CLIENTE"]
        client_address = latest_record.get(NOME_COLUNA_ENDERECO, "N/A")
        client_phone = latest_record.get(NOME_COLUNA_TELEFONE, "N/A")
        client_city = latest_record.get("NO_CIDADE", "N/A")
        modelo_mais_comprado = format_list(get_modes(client_df_sorted["Modelo"])) if "Modelo" in client_df_sorted.columns else "N/A"
        concessionario_mais_frequente = format_list(get_modes(client_df_sorted[NOME_COLUNA_CONCESSIONARIO])) if NOME_COLUNA_CONCESSIONARIO in client_df_sorted.columns else "N/A"

        st.subheader(f"Detalhes de: {client_name}")
        col1_info, col2_info = st.columns(2)
        with col1_info:
            st.markdown(f"<div class='info-card'><span class='label'>CNPJ:</span><span class='value'>{client_cnpj_formatted}</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='info-card'><span class='label'>Endereço:</span><span class='value'>{client_address}</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='info-card'><span class='label'>Modelo mais comprado:</span><span class='value'>{modelo_mais_comprado}</span></div>", unsafe_allow_html=True)
        with col2_info:
            st.markdown(f"<div class='info-card'><span class='label'>Cidade:</span><span class='value'>{client_city}</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='info-card'><span class='label'>Telefone:</span><span class='value'>{client_phone}</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='info-card'><span class='label'>Concessionário mais frequente:</span><span class='value'>{concessionario_mais_frequente}</span></div>", unsafe_allow_html=True)

        st.markdown("#### Análise e Histórico")
        total_purchases = len(client_df_sorted)
        first_purchase_date = client_df_sorted["Data emplacamento"].min()
        last_purchase_date = client_df_sorted["Data emplacamento"].max()
        valid_purchase_dates = client_df_sorted["Data emplacamento"].dropna().tolist()
        prediction_text, predicted_next_date = calculate_next_purchase_prediction(valid_purchase_dates)
        sales_pitch = get_sales_pitch(last_purchase_date, predicted_next_date, total_purchases)
        col1_insight, col2_predict = st.columns(2)
        with col1_insight:
            st.markdown(f"**Insight de Vendas:**")
            st.info(sales_pitch)
        with col2_predict:
            st.markdown(f"**Previsão de Próxima Compra:**")
            st.info(prediction_text)
        col1_metric, col2_metric, col3_metric = st.columns(3)
        col1_metric.metric("Total de Emplacamentos", total_purchases)
        col2_metric.metric("Primeira Compra", first_purchase_date.strftime("%d/%m/%Y") if pd.notna(first_purchase_date) else "N/A")
        col3_metric.metric("Última Compra", last_purchase_date.strftime("%d/%m/%Y") if pd.notna(last_purchase_date) else "N/A")
        st.markdown("##### Histórico de Emplacamentos")
        cols_hist = ["Data emplacamento", "PLACA", "Chassi", "Marca", "Modelo", "Segmento", NOME_COLUNA_CONCESSIONARIO]
        cols_hist = [col for col in cols_hist if col in client_df_sorted.columns]
        client_df_display = client_df_sorted[cols_hist].rename(columns={
            "Data emplacamento": "Data",
            "PLACA": "Placa",
            "Chassi": "Chassi",
            "Marca": "Marca",
            "Modelo": "Modelo",
            "Segmento": "Segmento",
            NOME_COLUNA_CONCESSIONARIO: "Concessionário"
        })
        if "Data" in client_df_display.columns:
            client_df_display["Data"] = pd.to_datetime(client_df_display["Data"], errors="coerce").dt.strftime("%d/%m/%Y")
        st.dataframe(client_df_display, use_container_width=True)
else:
    st.subheader("Resumo Geral da Base de Dados")
    st.markdown("*(Considerando os filtros aplicados na barra lateral, se houver)*")
    if df_display.empty:
        st.warning("Nenhum dado disponível para exibir com os filtros selecionados.")
    else:
        total_emplacamentos = len(df_display)
        total_clientes = df_display["CNPJ_NORMALIZED"].nunique()
        data_inicio = df_display["Data emplacamento"].min()
        data_fim = df_display["Data emplacamento"].max()
        col1_res, col2_res, col3_res = st.columns(3)
        col1_res.metric("Total de Emplacamentos", total_emplacamentos)
        col2_res.metric("Clientes Únicos", total_clientes)
        col3_res.metric("Período Coberto", f"{data_inicio.strftime('%m/%Y') if pd.notna(data_inicio) else 'N/A'} a {data_fim.strftime('%m/%Y') if pd.notna(data_fim) else 'N/A'}")
        st.markdown("#### Emplacamentos por Ano")
        emplac_por_ano = df_display.dropna(subset=["Ano"]).groupby("Ano").size().reset_index(name="Count")
        if not emplac_por_ano.empty:
            emplac_por_ano["Ano"] = emplac_por_ano["Ano"].astype(int)
            fig_ano = px.bar(emplac_por_ano, x="Ano", y="Count", title="Total de Emplacamentos por Ano", labels={'Ano': 'Ano', 'Count': 'Quantidade'})
            fig_ano.update_layout(xaxis_type='category')
            st.plotly_chart(fig_ano, use_container_width=True)
        else:
            st.info("Não há dados suficientes para gerar o gráfico de emplacamentos por ano.")
        st.markdown("#### Emplacamentos por Marca e Ano")
        emplac_marca_ano = df_display.dropna(subset=["Ano", "Marca"]).groupby(["Ano", "Marca"]).size().reset_index(name="Count")
        if not emplac_marca_ano.empty:
            emplac_marca_ano["Ano"] = emplac_marca_ano["Ano"].astype(int)
            try:
                pivot_marca_ano = emplac_marca_ano.pivot(index="Marca", columns="Ano", values="Count").fillna(0).astype(int)
                pivot_marca_ano["Total"] = pivot_marca_ano.sum(axis=1)
                pivot_marca_ano = pivot_marca_ano.sort_values("Total", ascending=False)
                st.dataframe(pivot_marca_ano, use_container_width=True)
            except Exception as pivot_error:
                st.warning(f"Não foi possível gerar a tabela de emplacamentos por marca e ano: {pivot_error}")
        else:
            st.info("Não há dados suficientes para gerar a tabela de emplacamentos por marca e ano.")

st.sidebar.divider()
if os.path.exists(LOGO_WHITE_PATH):
    st.sidebar.image(LOGO_WHITE_PATH, width=150)
st.sidebar.markdown("© De Nigris Distribuidora")


# --- NOVO: Botão para listar clientes que compraram há mais de 1 ano e ainda não compraram em 2025 ---
st.divider()
st.subheader("📌 Oportunidades de Recompra")

if st.button("🔍 Listar Clientes Inativos ( > 1 ano sem comprar )"):
    hoje = pd.Timestamp.now()
    ano_atual = hoje.year

    # Última compra de cada cliente
    ultima_compra = df_display.groupby("CNPJ_NORMALIZED")["Data emplacamento"].max().reset_index()
    ultima_compra = ultima_compra.rename(columns={"Data emplacamento": "UltimaCompra"})

    # Total de compras por cliente
    total_compras = df_display.groupby("CNPJ_NORMALIZED").size().reset_index(name="TotalCompras")

    # Juntar infos
    clientes_info = pd.merge(ultima_compra, total_compras, on="CNPJ_NORMALIZED", how="left")

    # Clientes que não compraram no ano atual e cuja última compra foi há mais de 12 meses
    clientes_info = clientes_info[clientes_info["UltimaCompra"].notna()]
    clientes_info["MesesSemCompra"] = ((hoje - clientes_info["UltimaCompra"]) / pd.Timedelta(days=30)).astype(int)
    clientes_inativos = clientes_info[
        (clientes_info["UltimaCompra"].dt.year < ano_atual) & 
        (clientes_info["MesesSemCompra"] > 12)
    ].copy()

    if clientes_inativos.empty:
        st.success("✅ Nenhum cliente inativo encontrado! Todos os clientes ativos compraram no último ano.")
    else:
        # Trazer dados adicionais (Nome, CNPJ e Cidade)
        clientes_inativos = clientes_inativos.merge(
            df_display[["CNPJ_NORMALIZED", "NOME DO CLIENTE", "CNPJ CLIENTE", "NO_CIDADE"]].drop_duplicates(),
            on="CNPJ_NORMALIZED",
            how="left"
        )

        clientes_inativos = clientes_inativos[[
            "NOME DO CLIENTE", "CNPJ CLIENTE", "NO_CIDADE", "UltimaCompra", "TotalCompras", "MesesSemCompra"
        ]].sort_values(by="MesesSemCompra", ascending=False)

        clientes_inativos["UltimaCompra"] = clientes_inativos["UltimaCompra"].dt.strftime("%d/%m/%Y")

        st.warning(f"🚨 {len(clientes_inativos)} clientes estão há mais de 1 ano sem comprar!")

        st.dataframe(clientes_inativos, use_container_width=True)

        # Botão para download em XLSX
        excel_buffer = BytesIO()
        clientes_inativos.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        st.download_button(
            label="📥 Baixar Lista de Clientes Inativos (XLSX)",
            data=excel_buffer,
            file_name="clientes_inativos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
