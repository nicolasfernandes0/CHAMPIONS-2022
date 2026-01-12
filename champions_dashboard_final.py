import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import http.client
from typing import Dict, Optional
import os

# Configuração da página
st.set_page_config(
    page_title="UEFA Champions League 2022/23 Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurações da API
API_KEY = "a6dc4855d9832ff4404f314aa3045bd1"
API_HOST = "v3.football.api-sports.io"
LEAGUE_ID = 2  # UEFA Champions League
SEASON = 2022

# Cache persistente para dados da API
@st.cache_data(persist="disk")
def fetch_all_data():
    """Busca todos os dados da API uma única vez"""
    data = {}
    
    try:
        conn = http.client.HTTPSConnection(API_HOST)
        headers = {'x-apisports-key': API_KEY}
        
        # 1. Buscar todas as partidas da temporada
        with st.spinner("🔄 Carregando dados da UEFA Champions League 2022/23..."):
            endpoint = f"/fixtures?league={LEAGUE_ID}&season={SEASON}"
            conn.request("GET", endpoint, headers=headers)
            res = conn.getresponse()
            
            if res.status == 200:
                fixture_data = json.loads(res.read().decode("utf-8"))
                data['fixtures'] = fixture_data
                st.success("✅ Dados de partidas carregados!")
            else:
                st.error(f"❌ Erro ao buscar partidas: Status {res.status}")
                return None
        
        # 2. Buscar tabela de classificação
        endpoint = f"/standings?league={LEAGUE_ID}&season={SEASON}"
        conn.request("GET", endpoint, headers=headers)
        res = conn.getresponse()
        
        if res.status == 200:
            standings_data = json.loads(res.read().decode("utf-8"))
            data['standings'] = standings_data
            st.success("✅ Tabela de classificação carregada!")
        
        conn.close()
        
        if 'fixtures' in data:
            return data
        else:
            return None
            
    except Exception as e:
        st.error(f"❌ Erro na conexão com a API: {str(e)}")
        return None

def process_fixture_data(fixture_data: Dict) -> pd.DataFrame:
    """Processa dados das partidas para DataFrame"""
    matches = []
    
    for match in fixture_data['response']:
        try:
            # Informações básicas da partida
            match_info = {
                'match_id': match['fixture']['id'],
                'date': match['fixture']['date'],
                'timestamp': match['fixture']['timestamp'],
                'status': match['fixture']['status']['short'],
                'status_long': match['fixture']['status']['long'],
                'round': match['league']['round'],
                'stage': match['league']['round'].split(' - ')[0] if ' - ' in match['league']['round'] else match['league']['round'],
                'group': match['league']['round'].split(' - ')[1] if ' - ' in match['league']['round'] else 'N/A',
                'venue': match['fixture']['venue']['name'] if match['fixture']['venue'] else 'Unknown',
                'city': match['fixture']['venue']['city'] if match['fixture']['venue'] else 'Unknown',
                'referee': match['fixture']['referee'],
                'attendance': match['fixture']['venue'].get('capacity') if match['fixture']['venue'] else None,
                
                # Time da casa
                'home_team': match['teams']['home']['name'],
                'home_id': match['teams']['home']['id'],
                'home_logo': match['teams']['home']['logo'],
                'home_winner': match['teams']['home']['winner'] if match['teams']['home']['winner'] is not None else False,
                
                # Time visitante
                'away_team': match['teams']['away']['name'],
                'away_id': match['teams']['away']['id'],
                'away_logo': match['teams']['away']['logo'],
                'away_winner': match['teams']['away']['winner'] if match['teams']['away']['winner'] is not None else False,
                
                # Placar
                'home_goals': match['goals']['home'],
                'away_goals': match['goals']['away'],
                'halftime_home': match['score']['halftime']['home'],
                'halftime_away': match['score']['halftime']['away'],
                'extratime_home': match['score']['extratime']['home'] if match['score']['extratime']['home'] is not None else 0,
                'extratime_away': match['score']['extratime']['away'] if match['score']['extratime']['away'] is not None else 0,
                'penalty_home': match['score']['penalty']['home'] if match['score']['penalty']['home'] is not None else 0,
                'penalty_away': match['score']['penalty']['away'] if match['score']['penalty']['away'] is not None else 0,
                
                # Estatísticas derivadas
                'total_goals': match['goals']['home'] + match['goals']['away'],
                'goal_difference': match['goals']['home'] - match['goals']['away'],
                'has_extratime': match['score']['extratime']['home'] is not None or match['score']['extratime']['away'] is not None,
                'has_penalties': match['score']['penalty']['home'] is not None or match['score']['penalty']['away'] is not None,
                
                # Resultado
                'winner': match['teams']['home']['name'] if match['teams']['home']['winner'] 
                         else match['teams']['away']['name'] if match['teams']['away']['winner'] 
                         else 'Draw',
                'result_type': 'Normal' if not match['score']['extratime']['home'] and not match['score']['penalty']['home']
                              else 'Prorrogação' if match['score']['extratime']['home'] is not None
                              else 'Pênaltis' if match['score']['penalty']['home'] is not None
                              else 'Normal'
            }
            matches.append(match_info)
        except Exception as e:
            continue
    
    df = pd.DataFrame(matches)
    
    # Converter tipos de dados
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['date_str'] = df['date'].dt.strftime('%d/%m/%Y %H:%M')
        df['month'] = df['date'].dt.month
        df['month_name'] = df['date'].dt.strftime('%B')
        df['day_of_week'] = df['date'].dt.day_name()
        
    return df

def process_standings_data(standings_data: Dict) -> pd.DataFrame:
    """Processa dados da tabela de classificação"""
    if not standings_data or 'response' not in standings_data:
        return pd.DataFrame()
    
    standings = []
    for league_data in standings_data['response']:
        if 'league' in league_data and 'standings' in league_data['league']:
            for group in league_data['league']['standings']:
                for team in group:
                    team_info = {
                        'rank': team['rank'],
                        'team': team['team']['name'],
                        'logo': team['team']['logo'],
                        'points': team['points'],
                        'goals_diff': team['goalsDiff'],
                        'group': team['group'] if 'group' in team else 'N/A',
                        'form': team['form'],
                        'description': team['description'] if 'description' in team else '',
                        
                        # Estatísticas totais
                        'played': team['all']['played'],
                        'won': team['all']['won'],
                        'draw': team['all']['draw'],
                        'lost': team['all']['lost'],
                        'goals_for': team['all']['goals']['for'],
                        'goals_against': team['all']['goals']['against'],
                        
                        # Estatísticas em casa
                        'home_played': team['home']['played'],
                        'home_won': team['home']['won'],
                        'home_draw': team['home']['draw'],
                        'home_lost': team['home']['lost'],
                        'home_goals_for': team['home']['goals']['for'],
                        'home_goals_against': team['home']['goals']['against'],
                        
                        # Estatísticas fora
                        'away_played': team['away']['played'],
                        'away_won': team['away']['won'],
                        'away_draw': team['away']['draw'],
                        'away_lost': team['away']['lost'],
                        'away_goals_for': team['away']['goals']['for'],
                        'away_goals_against': team['away']['goals']['against'],
                    }
                    standings.append(team_info)
    
    return pd.DataFrame(standings)

# Título e descrição
st.title("⚽ UEFA Champions League 2022/23")
st.markdown("### Dashboard Completo da Temporada")
st.markdown("---")

# Inicializar estado da sessão
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
    st.session_state.raw_data = None
    st.session_state.matches_df = pd.DataFrame()
    st.session_state.standings_df = pd.DataFrame()

# Função para carregar dados
def load_data():
    """Carrega dados da API e processa"""
    with st.spinner("🔄 Buscando dados da API Football..."):
        raw_data = fetch_all_data()
        
        if raw_data:
            st.session_state.raw_data = raw_data
            st.session_state.matches_df = process_fixture_data(raw_data['fixtures'])
            if 'standings' in raw_data:
                st.session_state.standings_df = process_standings_data(raw_data['standings'])
            st.session_state.data_loaded = True
            st.success("✅ Dados carregados com sucesso!")
            st.rerun()
        else:
            st.error("❌ Falha ao carregar dados. Verifique sua conexão e chave da API.")

# Sidebar
st.sidebar.header("⚙️ Configurações")

# Botão para carregar dados
if not st.session_state.data_loaded:
    if st.sidebar.button("📥 Carregar Dados da API", type="primary", use_container_width=True):
        load_data()
    
    st.sidebar.info("""
    ### Como usar:
    1. Clique em **"Carregar Dados da API"**
    2. Aguarde o carregamento (apenas uma vez)
    3. Explore o dashboard com os dados reais
    """)
    
    # Tela inicial sem dados
    st.info("""
    ## 🏆 Bem-vindo ao Dashboard da UEFA Champions League!
    
    Este dashboard apresenta uma análise completa da temporada 2022/23 da UEFA Champions League.
    
    **Para começar:**
    1. Clique no botão **"Carregar Dados da API"** na barra lateral
    2. Aguarde o carregamento dos dados (pode levar alguns segundos)
    3. Explore as estatísticas, gráficos e análises
    
    **Dados incluídos:**
    - Todas as 125+ partidas da temporada
    - Tabela de classificação dos grupos
    - Estatísticas detalhadas por time
    - Análises gráficas e métricas
    """)
    
    # Placeholders para visualizações
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Estatísticas")
        st.write("Dados serão exibidos aqui após o carregamento")
    with col2:
        st.subheader("📈 Gráficos")
        st.write("Gráficos interativos aparecerão aqui")
    
    st.stop()

# Se chegou aqui, os dados estão carregados
matches_df = st.session_state.matches_df
standings_df = st.session_state.standings_df

# Informações na sidebar
st.sidebar.success("✅ Dados carregados")
st.sidebar.metric("Total de Partidas", len(matches_df))
st.sidebar.metric("Times Participantes", matches_df['home_team'].nunique())
st.sidebar.metric("Total de Gols", matches_df['total_goals'].sum())

# Filtros na sidebar
st.sidebar.header("🔍 Filtros")

# Filtro por fase da competição
phase_options = sorted(matches_df['stage'].unique())
selected_phases = st.sidebar.multiselect(
    "Fase da Competição",
    options=phase_options,
    default=["Group A", "Group B", "Group C", "Group D", 
             "Group E", "Group F", "Group G", "Group H",
             "Round of 16", "Quarter-finals", "Semi-finals", "Final"]
)

# Filtro por resultado
result_options = ['Todos', 'Vitória Casa', 'Vitória Fora', 'Empate']
selected_result = st.sidebar.selectbox("Resultado", result_options, index=0)

# Filtro por mês
if 'month_name' in matches_df.columns:
    month_options = sorted(matches_df['month_name'].unique())
    selected_months = st.sidebar.multiselect("Mês", options=month_options, default=month_options)

# Aplicar filtros
filtered_df = matches_df.copy()

if selected_phases:
    filtered_df = filtered_df[filtered_df['stage'].isin(selected_phases)]

if selected_result == 'Vitória Casa':
    filtered_df = filtered_df[filtered_df['home_winner'] == True]
elif selected_result == 'Vitória Fora':
    filtered_df = filtered_df[filtered_df['away_winner'] == True]
elif selected_result == 'Empate':
    filtered_df = filtered_df[filtered_df['winner'] == 'Draw']

if 'selected_months' in locals() and selected_months:
    filtered_df = filtered_df[filtered_df['month_name'].isin(selected_months)]

# Métricas principais
st.header("📊 Visão Geral da Temporada")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_matches = len(filtered_df)
    total_all = len(matches_df)
    delta_matches = total_matches - total_all if total_matches != total_all else None
    st.metric("Partidas", total_matches, delta_matches)

with col2:
    total_goals = filtered_df['total_goals'].sum()
    total_all_goals = matches_df['total_goals'].sum()
    delta_goals = total_goals - total_all_goals if total_goals != total_all_goals else None
    st.metric("Total de Gols", total_goals, delta_goals)

with col3:
    avg_goals = round(filtered_df['total_goals'].mean(), 2)
    avg_all = round(matches_df['total_goals'].mean(), 2)
    delta_avg = round(avg_goals - avg_all, 2) if avg_goals != avg_all else None
    st.metric("Média Gols/Partida", avg_goals, delta_avg)

with col4:
    home_wins = len(filtered_df[filtered_df['home_winner'] == True])
    home_rate = round((home_wins / total_matches) * 100, 1) if total_matches > 0 else 0
    st.metric("Vitórias em Casa", f"{home_wins} ({home_rate}%)")

st.markdown("---")

# Análises em abas
tab1, tab2, tab3, tab4 = st.tabs(["📈 Estatísticas Gerais", "🏆 Classificação", "⚽ Partidas", "📊 Análises Avançadas"])

with tab1:
    st.subheader("📈 Estatísticas Gerais da Temporada")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribuição de resultados
        results = filtered_df['winner'].value_counts()
        results_df = pd.DataFrame({
            'Resultado': results.index,
            'Quantidade': results.values
        })
        
        # Renomear para melhor visualização
        results_df['Resultado'] = results_df['Resultado'].apply(
            lambda x: 'Empate' if x == 'Draw' else f"Vitória {x.split()[-1] if len(x.split()) > 1 else x}"
        )
        
        fig = px.pie(
            results_df,
            values='Quantidade',
            names='Resultado',
            title="Distribuição de Resultados",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Gols por fase
        if 'stage' in filtered_df.columns:
            goals_by_stage = filtered_df.groupby('stage')['total_goals'].sum().reset_index()
            goals_by_stage = goals_by_stage.sort_values('total_goals', ascending=False)
            
            fig = px.bar(
                goals_by_stage,
                x='stage',
                y='total_goals',
                title="Total de Gols por Fase",
                color='total_goals',
                color_continuous_scale='Blues'
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    
    # Histograma de gols por partida
    st.subheader("Distribuição de Gols por Partida")
    
    fig = px.histogram(
        filtered_df,
        x='total_goals',
        nbins=15,
        title="Frequência de Total de Gols por Partida",
        labels={'total_goals': 'Total de Gols', 'count': 'Número de Partidas'},
        color_discrete_sequence=['#1f77b4']
    )
    fig.update_layout(bargap=0.1)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("🏆 Tabela de Classificação")
    
    if not standings_df.empty:
        # Mostrar por grupos
        groups = sorted([g for g in standings_df['group'].unique() if g != 'N/A'])
        
        for group in groups:
            st.markdown(f"### Grupo {group}")
            group_df = standings_df[standings_df['group'] == group].sort_values('rank')
            
            # Formatar tabela
            display_df = group_df[['rank', 'team', 'points', 'played', 'won', 'draw', 'lost', 
                                  'goals_for', 'goals_against', 'goals_diff']].copy()
            
            # Adicionar porcentagem de aproveitamento
            display_df['aproveitamento'] = (display_df['points'] / (display_df['played'] * 3) * 100).round(1)
            
            st.dataframe(
                display_df.style.format({
                    'aproveitamento': '{:.1f}%'
                }).background_gradient(subset=['points'], cmap='YlOrRd'),
                use_container_width=True,
                hide_index=True
            )
    
    # Top 5 times com mais gols
    st.subheader("🎯 Times Mais Ofensivos")
    
    # Calcular estatísticas por time
    team_stats = []
    all_teams = set(filtered_df['home_team'].unique()) | set(filtered_df['away_team'].unique())
    
    for team in all_teams:
        home_matches = filtered_df[filtered_df['home_team'] == team]
        away_matches = filtered_df[filtered_df['away_team'] == team]
        
        total_matches_team = len(home_matches) + len(away_matches)
        if total_matches_team == 0:
            continue
        
        goals_for = home_matches['home_goals'].sum() + away_matches['away_goals'].sum()
        goals_against = home_matches['away_goals'].sum() + away_matches['home_goals'].sum()
        
        team_stats.append({
            'Time': team,
            'Jogos': total_matches_team,
            'Gols Pró': goals_for,
            'Gols Contra': goals_against,
            'Saldo': goals_for - goals_against,
            'Média Gols/Partida': round(goals_for / total_matches_team, 2)
        })
    
    if team_stats:
        teams_df = pd.DataFrame(team_stats).sort_values('Gols Pró', ascending=False).head(10)
        
        fig = px.bar(
            teams_df,
            x='Time',
            y='Gols Pró',
            title="Top 10 Times - Gols Pró",
            color='Gols Pró',
            text='Gols Pró'
        )
        fig.update_traces(texttemplate='%{text}', textposition='outside')
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("⚽ Partidas da Temporada")
    
    # Filtro adicional para partidas
    search_team = st.text_input("🔍 Buscar por time:", "")
    
    if search_team:
        matches_to_show = filtered_df[
            (filtered_df['home_team'].str.contains(search_team, case=False)) | 
            (filtered_df['away_team'].str.contains(search_team, case=False))
        ]
    else:
        matches_to_show = filtered_df
    
    # Ordenar opções
    sort_by = st.selectbox("Ordenar por:", ['Data (Mais Recente)', 'Data (Mais Antigo)', 'Mais Gols', 'Menos Gols'])
    
    if sort_by == 'Data (Mais Recente)':
        matches_to_show = matches_to_show.sort_values('date', ascending=False)
    elif sort_by == 'Data (Mais Antigo)':
        matches_to_show = matches_to_show.sort_values('date', ascending=True)
    elif sort_by == 'Mais Gols':
        matches_to_show = matches_to_show.sort_values('total_goals', ascending=False)
    elif sort_by == 'Menos Gols':
        matches_to_show = matches_to_show.sort_values('total_goals', ascending=True)
    
    # Mostrar partidas
    for idx, match in matches_to_show.head(30).iterrows():
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 3])
            
            with col1:
                st.markdown(f"**{match['home_team']}**")
                st.caption(f"Casa • {match['venue']}")
            
            with col2:
                st.markdown(f"### {match['home_goals']}")
            
            with col3:
                st.markdown(f"### {match['away_goals']}")
            
            with col4:
                st.markdown(f"**{match['away_team']}**")
                st.caption(f"Fora • {match['city']}")
            
            # Informações adicionais
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.caption(f"📅 {match['date_str']}")
            with col_info2:
                st.caption(f"📋 {match['round']}")
            with col_info3:
                if match['has_extratime']:
                    st.caption(f"⚡ Prorrogação: {match['extratime_home']}-{match['extratime_away']}")
                elif match['has_penalties']:
                    st.caption(f"🎯 Pênaltis: {match['penalty_home']}-{match['penalty_away']}")
            
            st.divider()

with tab4:
    st.subheader("📊 Análises Avançadas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gols por mês
        if 'month_name' in filtered_df.columns:
            monthly_goals = filtered_df.groupby('month_name')['total_goals'].sum().reset_index()
            
            # Ordenar por ordem cronológica
            month_order = ['June', 'July', 'August', 'September', 'October', 
                          'November', 'December', 'January', 'February', 
                          'March', 'April', 'May', 'June']
            monthly_goals['month_name'] = pd.Categorical(
                monthly_goals['month_name'], 
                categories=[m for m in month_order if m in monthly_goals['month_name'].unique()],
                ordered=True
            )
            monthly_goals = monthly_goals.sort_values('month_name')
            
            fig = px.line(
                monthly_goals,
                x='month_name',
                y='total_goals',
                title="Evolução de Gols por Mês",
                markers=True,
                line_shape='spline'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Média de gols por dia da semana
        if 'day_of_week' in filtered_df.columns:
            weekday_goals = filtered_df.groupby('day_of_week').agg({
                'total_goals': ['sum', 'mean', 'count']
            }).reset_index()
            
            weekday_goals.columns = ['Dia', 'Total_Gols', 'Media_Gols', 'Partidas']
            
            # Ordenar por dias da semana
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                        'Friday', 'Saturday', 'Sunday']
            weekday_goals['Dia'] = pd.Categorical(
                weekday_goals['Dia'], 
                categories=day_order,
                ordered=True
            )
            weekday_goals = weekday_goals.sort_values('Dia')
            
            fig = px.bar(
                weekday_goals,
                x='Dia',
                y='Media_Gols',
                title="Média de Gols por Dia da Semana",
                color='Media_Gols',
                text='Media_Gols'
            )
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
    
    # Heatmap de confrontos (se houver tempo)
    st.subheader("🔥 Confrontos Diretos")
    
    # Selecionar dois times para comparação
    top_teams = sorted(matches_df['home_team'].value_counts().head(10).index.tolist())
    
    if len(top_teams) >= 2:
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            team1 = st.selectbox("Selecione o Time 1:", top_teams, index=0)
        with col_sel2:
            team2 = st.selectbox("Selecione o Time 2:", [t for t in top_teams if t != team1], index=1)
        
        # Buscar confrontos diretos
        direct_matches = matches_df[
            ((matches_df['home_team'] == team1) & (matches_df['away_team'] == team2)) |
            ((matches_df['home_team'] == team2) & (matches_df['away_team'] == team1))
        ]
        
        if not direct_matches.empty:
            st.write(f"**Histórico de Confrontos: {team1} vs {team2}**")
            
            for _, match in direct_matches.iterrows():
                winner_text = ""
                if match['winner'] == team1:
                    winner_text = f"✅ **{team1} venceu**"
                elif match['winner'] == team2:
                    winner_text = f"✅ **{team2} venceu**"
                else:
                    winner_text = "🤝 **Empate**"
                
                st.write(f"{match['date_str']}: {match['home_team']} {match['home_goals']} - {match['away_goals']} {match['away_team']} • {winner_text} ({match['round']})")
            
            # Estatísticas do confronto
            team1_wins = len(direct_matches[direct_matches['winner'] == team1])
            team2_wins = len(direct_matches[direct_matches['winner'] == team2])
            draws = len(direct_matches[direct_matches['winner'] == 'Draw'])
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric(f"Vitórias {team1}", team1_wins)
            with col_stat2:
                st.metric("Empates", draws)
            with col_stat3:
                st.metric(f"Vitórias {team2}", team2_wins)
        else:
            st.info(f"Não há confrontos diretos entre {team1} e {team2} nesta temporada.")

# Exportar dados
st.sidebar.header("📥 Exportar Dados")

if st.sidebar.button("💾 Exportar para CSV", use_container_width=True):
    csv = matches_df.to_csv(index=False)
    st.sidebar.download_button(
        label="Baixar CSV",
        data=csv,
        file_name="uefa_champions_league_2022_23.csv",
        mime="text/csv"
    )

# Informações finais
st.sidebar.markdown("---")
st.sidebar.markdown("""
### ℹ️ Sobre os Dados
- **Temporada:** 2022/23
- **Competição:** UEFA Champions League
- **Fonte:** API-Football
- **Carregamento:** Único ao iniciar
- **Partidas:** Todas as fases
""")

# Rodapé
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
        <p>Dashboard desenvolvido com Streamlit • Dados via API-Football</p>
        <p>UEFA Champions League 2022/23 • Dados carregados uma única vez da API</p>
    </div>
    """,
    unsafe_allow_html=True
)