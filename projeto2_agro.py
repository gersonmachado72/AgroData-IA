# ==========================================
# PROJETO 2: Assistente de Análise Agrícola
# Versão Corrigida - SDK Antigo (google.generativeai)
# ==========================================

import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import re
import sys
import io
import matplotlib.pyplot as plt
import time
from datetime import datetime, timedelta
import random

# 1. Configuração da API Gemini (SDK antigo)
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    st.error("Configure a variável GEMINI_API_KEY no terminal.")
    st.stop()

# Configurar a API com a chave
genai.configure(api_key=API_KEY)

st.set_page_config(page_title="AgroFinanceiro IA", page_icon="💰", layout="wide")
st.title("🌾 AgroData IA - Gestão e Finanças")

# 2. Classe para controle de rate limiting
class RateLimiter:
    def __init__(self, max_requests_per_minute=50, max_requests_per_day=1000):
        self.max_per_minute = max_requests_per_minute
        self.max_per_day = max_requests_per_day
        self.requests = []
        self.daily_requests = []
    
    def can_make_request(self):
        now = datetime.now()
        
        # Limpar requisições antigas (> 1 minuto)
        self.requests = [req for req in self.requests 
                        if req > now - timedelta(minutes=1)]
        
        # Limpar requisições antigas (> 24 horas)
        self.daily_requests = [req for req in self.daily_requests 
                              if req > now - timedelta(days=1)]
        
        # Verificar limites
        if len(self.requests) >= self.max_per_minute:
            return False, f"Limite por minuto excedido ({self.max_per_minute})"
        
        if len(self.daily_requests) >= self.max_per_day:
            return False, f"Limite diário excedido ({self.max_per_day})"
        
        return True, "OK"
    
    def register_request(self):
        now = datetime.now()
        self.requests.append(now)
        self.daily_requests.append(now)
    
    def get_wait_time(self):
        if not self.requests:
            return 0
        
        now = datetime.now()
        oldest = min(self.requests)
        time_to_wait = (oldest + timedelta(minutes=1) - now).total_seconds()
        return max(0, time_to_wait) + random.uniform(1, 3)

# Inicializar rate limiter na sessão
if 'rate_limiter' not in st.session_state:
    st.session_state.rate_limiter = RateLimiter()

# 3. Função para Carregar e Calcular Dados
def carregar_e_processar():
    try:
        df = pd.read_csv("dados_fazenda.csv")
        # Converter colunas para numérico com tratamento adequado
        for col in ['Producao_Sacas', 'Preco_Saca', 'Gasto_Insumo']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Calcular total recebido (evitando o warning de downcasting)
        df['Total_Recebido'] = 0.0  # Inicializar como float
        if all(col in df.columns for col in ['Producao_Sacas', 'Preco_Saca', 'Gasto_Insumo']):
            mask = df['Producao_Sacas'].notna() & df['Preco_Saca'].notna() & df['Gasto_Insumo'].notna()
            df.loc[mask, 'Total_Recebido'] = (
                df.loc[mask, 'Producao_Sacas'] * df.loc[mask, 'Preco_Saca'] - df.loc[mask, 'Gasto_Insumo']
            )
        return df
    except FileNotFoundError:
        # Criar dataframe vazio com estrutura padrão
        return pd.DataFrame(columns=['Data', 'Talhao', 'Cultura', 'Producao_Sacas', 
                                    'Preco_Saca', 'Chuva_mm', 'Gasto_Insumo', 'Total_Recebido'])

# Inicializar dados na sessão
if 'dados' not in st.session_state:
    st.session_state.dados = carregar_e_processar()

# 4. Área de Visualização e Edição
st.subheader("📊 Painel de Dados Financeiros")

edited_df = st.data_editor(
    st.session_state.dados,
    num_rows="dynamic",
    width='stretch',
    column_config={
        "Total_Recebido": st.column_config.NumberColumn(
            "Total Recebido (R$)", 
            disabled=True,
            format="R$ %.2f"
        ),
        "Producao_Sacas": st.column_config.NumberColumn(
            "Produção (Sacas)",
            min_value=0,
            step=1
        ),
        "Preco_Saca": st.column_config.NumberColumn(
            "Preço por Saca (R$)",
            min_value=0,
            format="R$ %.2f"
        ),
        "Gasto_Insumo": st.column_config.NumberColumn(
            "Gasto com Insumos (R$)",
            min_value=0,
            format="R$ %.2f"
        )
    },
    key="data_editor"
)

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("💾 Salvar Alterações", type="primary"):
        edited_df = edited_df.copy()
        edited_df['Total_Recebido'] = 0.0
        mask = (edited_df['Producao_Sacas'].notna() & 
                edited_df['Preco_Saca'].notna() & 
                edited_df['Gasto_Insumo'].notna())
        edited_df.loc[mask, 'Total_Recebido'] = (
            edited_df.loc[mask, 'Producao_Sacas'].astype(float) * 
            edited_df.loc[mask, 'Preco_Saca'].astype(float) - 
            edited_df.loc[mask, 'Gasto_Insumo'].astype(float)
        )
        
        st.session_state.dados = edited_df
        st.session_state.dados.to_csv("dados_fazenda.csv", index=False)
        st.success("✅ Dados salvos com sucesso!")
        time.sleep(1)
        st.rerun()

with col2:
    if st.button("➕ Adicionar Linha"):
        nova_linha = pd.DataFrame([{col: None for col in st.session_state.dados.columns}])
        st.session_state.dados = pd.concat([st.session_state.dados, nova_linha], 
                                           ignore_index=True, 
                                           sort=False)
        st.rerun()

with col3:
    if st.button("🔄 Resetar"):
        st.session_state.dados = carregar_e_processar()
        st.rerun()

# Mostrar total acumulado
st.markdown("---")
col_metric1, col_metric2, col_metric3 = st.columns(3)

with col_metric1:
    total_recebido = st.session_state.dados['Total_Recebido'].sum()
    st.metric("💰 Total Recebido", f"R$ {total_recebido:,.2f}")

with col_metric2:
    total_producao = st.session_state.dados['Producao_Sacas'].sum()
    st.metric("🌾 Produção Total", f"{total_producao:,.0f} sacas")

with col_metric3:
    total_gastos = st.session_state.dados['Gasto_Insumo'].sum()
    st.metric("📉 Total Gastos", f"R$ {total_gastos:,.2f}")

# 5. Área de Ações
st.markdown("---")
col_acoes = st.columns([1])[0]  # Apenas uma coluna para ações

with col_acoes:
    st.subheader("📤 Exportar Dados")
    
    if st.checkbox("📊 Ver status da cota da API"):
        can_request, message = st.session_state.rate_limiter.can_make_request()
        if can_request:
            st.success("✅ API disponível para consultas")
        else:
            wait_time = st.session_state.rate_limiter.get_wait_time()
            st.warning(f"⏳ API em limite: {message}. Aguarde {wait_time:.0f}s")
    
    opcoes = st.multiselect(
        "Opções de exportação:", 
        ["Imprimir Relatório", "Baixar CSV", "Ver Estatísticas"]
    )
    
    if "Baixar CSV" in opcoes:
        csv = st.session_state.dados.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"dados_fazenda_{time.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    if "Imprimir Relatório" in opcoes:
        if st.button("🖨️ Gerar Relatório"):
            st.components.v1.html("""
                <script>
                    window.print();
                </script>
            """, height=0)
    
    if "Ver Estatísticas" in opcoes:
        st.subheader("📊 Estatísticas Rápidas")
        st.write(st.session_state.dados.describe())