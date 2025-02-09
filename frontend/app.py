import streamlit as st
import plotly.graph_objects as go
from utils import(
    get_documentation, 
    is_payload_ok, 
    request_data,
    msg_balance
)
from plots import (
    plot_gauge_global_scores, 
    plot_gauge_financial_scores,
)

docs = get_documentation()

st.set_page_config(layout="wide", page_title="VAL")
_, content, _ = st.columns([1, 4, 1])


# state to give time to the api processing
if 'is_streaming' not in st.session_state:
    st.session_state.is_streaming = False

if 'api_response' not in st.session_state:
    st.session_state.api_response = None

if 'input_request' not in st.session_state:
    st.session_state.input_request = None

if 'is_streaming_detail_salud_financiera' not in st.session_state:
    st.session_state.is_streaming_detail_salud_financiera = False

if 'is_streaming_detail_precio_historico' not in st.session_state:
    st.session_state.is_streaming_detail_precio_historico = False

if 'is_streaming_detail_precio_competencia' not in st.session_state:
    st.session_state.is_streaming_detail_precio_competencia = False


with content:

    # Streamlit App
    st.title('📈 Análisis Fundamental para empresas que cotizan en bolsa')
    st.markdown(docs['introduction'])

    # Input section
    st.header('1️⃣ Ingrese el Ticker de la empresa')
    ticker = st.text_input("Ticker")

    st.header('2️⃣ Pesos Financieros')
    st.markdown(docs['financial_weights'])

    # Growth Weight Slider
    growth_weight = round(st.slider('**Peso de crecimiento:**', 0.0, 1.0, 0.5), 2)

    # Automatically compute Peers Weight
    peers_weight = round(st.slider('**Peso de la competencia:**', 0.0, 1.0, 1-growth_weight, disabled=True), 2)

    financial_weights = {"income": {"growth": growth_weight, "peers": peers_weight}}

    # Peers section
    st.header('3️⃣ Competidores')
    st.markdown(docs['competitors_weights'])

    num_competitors = st.number_input('**Número de competidores**', min_value=1, value=2)
    is_custom = st.radio('**Te gustaría ingresar manualmente los competidores de la empresa?**', ('Si', 'No'), index=1)

    if is_custom == 'Si':
        total_peers_w_1 = 0
        custom_peers = {}
        st.markdown('**Ingresa cada competidor y su respectivo peso:**')
        n_iter = num_competitors if num_competitors==1 else num_competitors-1
        for i in range(n_iter):
            col1_peers, col2_peers = st.columns(2)
            with col1_peers:
                competitor_ticker = st.text_input(f'**Ticker del competidor {i+1}**')
            with col2_peers:
                competitor_weight = round(st.slider(f'**Peso del competidor {i+1}**', 0.0, 1.0, 1.0/num_competitors), 2)
            
            total_peers_w_1 += competitor_weight
            custom_peers[competitor_ticker] = {"weight": competitor_weight}

        if num_competitors>1:
            col1_peers, col2_peers = st.columns(2)
            with col1_peers:
                competitor_ticker = st.text_input(f'**Ticker del competidor {num_competitors}**')
            with col2_peers:
                competitor_weight = round(st.slider(f'**Peso del competidor {num_competitors}**', 0.0, 1.0, 1-total_peers_w_1, disabled=True), 2)
            
            total_peers_w = total_peers_w_1 + abs(competitor_weight)
            custom_peers[competitor_ticker] = {"weight": competitor_weight}

            if total_peers_w>1:
                st.error(f"Los pesos de los competidores debe sumar 1. Actualmente suma={total_peers_w}")

        peers = {"custom": custom_peers, "n_competitors": None}
    else:
        peers = {"custom": None, "n_competitors": num_competitors}

    # Multiples Weights section
    st.header('4️⃣ Pesos de los multiplos analizar')
    st.markdown(docs["multiples_weights"])
    pe_ratio_weight = st.slider('**PE Ratio**', 0.0, 1.0, 0.25)
    ps_ratio_weight = st.slider('**PS Ratio**', 0.0, 1.0, 0.25)
    pgp_ratio_weight = st.slider('**PGP Ratio**', 0.0, 1.0, 0.25)

    pfcf_ratio_aux = 1-(pe_ratio_weight+ps_ratio_weight+pgp_ratio_weight)
    pfcf_ratio_weight = st.slider('**PFCF Ratio**', 0.0, 1.0, pfcf_ratio_aux, disabled=True)

    total_ratios_weight = round(
        pe_ratio_weight+
        ps_ratio_weight+
        pgp_ratio_weight+
        abs(pfcf_ratio_weight), 
    2)  
    if total_ratios_weight>1:
        st.error(f"Error PE Ratio + PS Ratio + PGP Ratio + PFCF Ratio = {total_ratios_weight}.\nDebe sumar 1. ")

    multiples_weights = {
        "pe_ratio": pe_ratio_weight,
        "ps_ratio": ps_ratio_weight,
        "pgp_ratio": pgp_ratio_weight,
        "pfcf_ratio": pfcf_ratio_weight
    }
    payload = {
        "ticker": ticker,
        "financial_weights": financial_weights,
        "peers": peers,
        "multiples_weights": multiples_weights
    }
    st.session_state.input_request = payload
    
    # st.json(payload)  # Show the payload
    st.markdown("---")

    # Submit button
    if st.button('🚀 Evaluar Empresa', use_container_width=True, disabled=(not is_payload_ok(payload))):
        with st.spinner("Procesando..."):
            # request data
            st.session_state.api_response = request_data(payload)
            st.session_state.is_streaming = True
    
    if st.session_state.is_streaming:
        st.markdown(f'<div style="text-align: center; font-size: 34px"> {docs["disclaimer"]} </div>', unsafe_allow_html=True)
        st.markdown("---")
        scores = st.session_state.api_response
        fig_financial, fig_historic, fig_competitors = plot_gauge_global_scores(scores)
        layout = go.Layout(
            autosize=True,
            height=300,
            grid = {'rows': 1, 'columns': 3, 'pattern': "independent"},
        )
        fig = go.Figure(layout=layout)
        fig.add_trace(fig_financial)
        fig.add_trace(fig_historic)
        fig.add_trace(fig_competitors)
        
        st.markdown('<div style="text-align: center; font-size: 34px"> Calificación </div>', unsafe_allow_html=True)
        st.plotly_chart(fig)

        col_detalle = st.columns(3)
        with col_detalle[0]:
            if st.button('Ver detalle salud financiera', use_container_width=True):
                st.session_state.is_streaming_detail_salud_financiera = True
                st.session_state.is_streaming_detail_precio_historico = False
                st.session_state.is_streaming_detail_precio_competencia = False
        with col_detalle[1]:
            if st.button('Ver detalle precio historico', use_container_width=True):
                st.session_state.is_streaming_detail_salud_financiera = False
                st.session_state.is_streaming_detail_precio_historico = True
                st.session_state.is_streaming_detail_precio_competencia = False
        with col_detalle[2]:
            if st.button('Ver detalle precio competencia', use_container_width=True):
                st.session_state.is_streaming_detail_salud_financiera = False
                st.session_state.is_streaming_detail_precio_historico = False
                st.session_state.is_streaming_detail_precio_competencia = True

        if st.session_state.is_streaming_detail_salud_financiera:
            st.markdown("---")
            st.markdown("\n\n")
            st.markdown('<div style="text-align: center; font-size: 30px"> Detalle de Calificación Salud Financiera </div>', unsafe_allow_html=True)
            st.markdown("\n\n")
            st.markdown(docs["detail_financial"])
            fig_income, fig_balance, fig_cash = plot_gauge_financial_scores(scores)
            layout = go.Layout(
                autosize=True,
                height=300,
                grid = {'rows': 1, 'columns': 3, 'pattern': "independent"},
            )
            fig = go.Figure(layout=layout)
            fig.add_trace(fig_income)
            fig.add_trace(fig_balance)
            fig.add_trace(fig_cash)
            st.plotly_chart(fig)

            col_salud_financiera = st.columns(3)
            with col_salud_financiera[0]: # income column
                inc_growth = scores["income_indicator_growth"]
                st.markdown('<div style="text-align: center; font-size: 20px">¿La empresa viene creciendo?</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="text-align: center; font-size: 15px">Score de crecimiento: {inc_growth}</div>', unsafe_allow_html=True)
                st.dataframe(
                    scores["income_df"],
                    column_config={
                        "data": st.column_config.BarChartColumn("Info ultimos 6 años", width="medium"),
                    },
                    use_container_width=True
                )

                inc_margins = scores["income_indicator_margins_peer"]
                st.markdown('<div style="text-align: center; font-size: 20px">¿Cómo están los margenes vs la competencia?</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="text-align: center; font-size: 15px">Score de margenes: {inc_margins}</div>', unsafe_allow_html=True)
                st.dataframe(scores["margins_df"], use_container_width=True)
                
            with col_salud_financiera[1]: # balance column
                st.markdown('<div style="text-align: center; font-size: 20px">¿Qué tan sana se encuentra la empresa?</div>', unsafe_allow_html=True)
                st.markdown("\n\n")
                # meses de operacion
                value, rule, decision = scores["balance_months_operation"].values()
                st.metric(f'Meses de operación > {rule}?  {msg_balance(decision)}', value, border=True)
                
                # current ratio
                value, rule, decision = scores["balance_current_ratio"].values()
                st.metric(f'Current Ratio > {rule}?  {msg_balance(decision)}', value, border=True)

                # Quick ratio
                value, rule, decision = scores["balance_quick_ratio"].values()
                st.metric(f'Quick Ratio > {rule}?  {msg_balance(decision)}', value, border=True)

                # Debt ratio
                value, rule, decision = scores["balance_debt_ratio"].values()
                st.metric(f'Debt Ratio < {rule}?  {msg_balance(decision)}', value, border=True)

            with col_salud_financiera[2]:
                st.markdown('<div style="text-align: center; font-size: 20px">¿El flujo de caja viene creciendo?</div>', unsafe_allow_html=True)
                st.markdown("\n\n")
                st.bar_chart(
                    scores["cash_flow_df"],
                    x = "Fecha",
                    y="Operating Cash Flow",
                    height=250
                )
                st.bar_chart(
                    scores["cash_flow_df"],
                    x = "Fecha",
                    y="Free Cash Flow",
                    height=250
                )

        if st.session_state.is_streaming_detail_precio_historico:
            st.markdown("---")
            st.markdown("\n\n")
            st.markdown('<div style="text-align: center; font-size: 30px"> Detalle de Calificación Precio Histórico </div>', unsafe_allow_html=True)
            st.markdown("\n\n")
            st.markdown(docs["detail_historic_price"])
            st.dataframe(scores["price_historic_multiples_df"], use_container_width=True)

        if st.session_state.is_streaming_detail_precio_competencia:
            st.markdown("---")
            st.markdown("\n\n")
            st.markdown('<div style="text-align: center; font-size: 30px"> Detalle de Calificación Precio vs Competencia </div>', unsafe_allow_html=True)
            st.markdown("\n\n")
            st.markdown(docs["detail_peers_price"])
            st.dataframe(scores["price_competitors_peers_df"], use_container_width=True)

        st.markdown("---")


    st.markdown(":link: Elaborado por: https://www.linkedin.com/in/sjimenezp/")