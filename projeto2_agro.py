# ==========================================
# PROJETO 2: Assistente de Análise Agrícola
# Versão Final - SEM matplotlib (usando apenas Streamlit)
# ==========================================

import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

st.set_page_config(page_title="AgroFinanceiro IA", page_icon="💰", layout="wide")
st.title("🌾 AgroData IA - Gestão e Finanças")

# Função para Carregar e Calcular Dados
def carregar_e_processar():
    try:
        df = pd.read_csv("dados_fazenda.csv")
        # Converter colunas para numérico
        for col in ['Producao_Sacas', 'Preco_Saca', 'Gasto_Insumo']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Calcular total recebido
        df['Total_Recebido'] = 0.0
        if all(col in df.columns for col in ['Producao_Sacas', 'Preco_Saca', 'Gasto_Insumo']):
            mask = df['Producao_Sacas'].notna() & df['Preco_Saca'].notna() & df['Gasto_Insumo'].notna()
            df.loc[mask, 'Total_Recebido'] = (
                df.loc[mask, 'Producao_Sacas'] * df.loc[mask, 'Preco_Saca'] - df.loc[mask, 'Gasto_Insumo']
            )
        return df
    except FileNotFoundError:
        # Criar dataframe vazio
        return pd.DataFrame(columns=['Data', 'Talhao', 'Cultura', 'Producao_Sacas', 
                                    'Preco_Saca', 'Chuva_mm', 'Gasto_Insumo', 'Total_Recebido'])

# Inicializar dados na sessão
if 'dados' not in st.session_state:
    st.session_state.dados = carregar_e_processar()

# Área de Visualização e Edição
st.subheader("📊 Painel de Dados Financeiros")

edited_df = st.data_editor(
    st.session_state.dados,
    num_rows="dynamic",
    use_container_width=True,
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

# Gráfico simples usando barras do Streamlit (opcional)
if len(st.session_state.dados) > 0 and 'Cultura' in st.session_state.dados.columns:
    st.markdown("---")
    st.subheader("📊 Produção por Cultura")
    
    # Agrupar por cultura
    producao_por_cultura = st.session_state.dados.groupby('Cultura')['Producao_Sacas'].sum().reset_index()
    
    # Usar bar_chart do Streamlit (não precisa de matplotlib)
    if not producao_por_cultura.empty:
        st.bar_chart(producao_por_cultura.set_index('Cultura'))

# Área de Exportação
st.markdown("---")
st.subheader("📤 Exportar Dados")

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

# Rodapé
st.markdown("---")
st.caption(f"🕒 Última atualização: {time.strftime('%d/%m/%Y %H:%M:%S')}")
