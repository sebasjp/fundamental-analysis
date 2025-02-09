import matplotlib.pyplot as plt
import plotly.graph_objects as go
from matplotlib.colors import Normalize, rgb2hex


def get_gauge(score: float):
        
    cmapR = plt.get_cmap('RdYlGn')
    norm = Normalize(vmin=0, vmax=10)
    colorbar = rgb2hex(cmapR(norm(score)))

    gauge = {
        'axis': {'range': [None, 10], 'tickwidth': 1},
        'bar': {'color': colorbar},
        'bgcolor': "white",
        'borderwidth': 2,
        'bordercolor': "gray",
    }
    return gauge


def plot_gauge_global_scores(scores: dict):

    
    fig_financial = go.Indicator(
        mode="gauge+number",
        value=scores['financial_indicator'],
        title={"text": "📈 Salud financiera", "font": {"color": "black"}},
        gauge=get_gauge(scores['financial_indicator']),
        domain = {'row': 0, 'column': 0}
    )
    # Plot Price Historic Indicator
    fig_historic = go.Indicator(
        mode="gauge+number",
        value=scores['price_historic_score'],
        title={"text": "💰 Precio Histórico", "font": {"color": "black"}},
        gauge=get_gauge(scores['price_historic_score']),
        domain = {'row': 0, 'column': 1}
    )
    # Plot Price Competitors Indicator
    fig_competitors = go.Indicator(
        mode="gauge+number",
        value=scores['price_competitors_score'],
        title={"text": "🏆 Precio vs competencia", "font": {"color": "black"}},
        gauge=get_gauge(scores['price_competitors_score']),
        domain = {'row': 0, 'column': 2}
    )
    return fig_financial, fig_historic, fig_competitors


def plot_gauge_financial_scores(scores: dict):

    
    fig_income = go.Indicator(
        mode="gauge+number",
        value=scores['income_indicator'],
        title={"text": "Estado de resultados", "font": {"color": "black"}},
        gauge=get_gauge(scores['income_indicator']),
        domain = {'row': 0, 'column': 0}
    )
    fig_balance = go.Indicator(
        mode="gauge+number",
        value=scores['balance_indicator'],
        title={"text": "Balance", "font": {"color": "black"}},
        gauge=get_gauge(scores['balance_indicator']),
        domain = {'row': 0, 'column': 1}
    )
    fig_cash = go.Indicator(
        mode="gauge+number",
        value=scores['cash_flow_indicator'],
        title={"text": "Flujo de caja", "font": {"color": "black"}},
        gauge=get_gauge(scores['cash_flow_indicator']),
        domain = {'row': 0, 'column': 2}
    )
    return fig_income, fig_balance, fig_cash

