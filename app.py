import streamlit as st
import sqlite3
import os
import pandas as pd
import plotly.express as px
import bcrypt
from datetime import datetime

st.set_page_config(page_title="Duarte Gestão", layout="wide")

# =========================
# ESTILO
# =========================
st.markdown("""
<style>
body {background:#0f172a;color:#e2e8f0;}
.card {
    background:#111827;
    padding:20px;
    border-radius:15px;
    margin-bottom:15px;
}
.title {font-size:28px;font-weight:bold;}
</style>
""", unsafe_allow_html=True)

# =========================
# DB
# =========================
def connect():
    os.makedirs("uploads", exist_ok=True)
    return sqlite3.connect("banco.db", check_same_thread=False)

def criar_tabelas():
    conn = connect()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        senha TEXT,
        admin INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        descricao TEXT,
        categoria TEXT,
        centro_custo TEXT,
        valor REAL,
        arquivos TEXT,
        status TEXT DEFAULT 'PENDENTE',
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_aprovacao TIMESTAMP,
        data_pagamento TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def criar_admin():
    conn = connect()
    senha_hash = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()
    try:
        conn.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?)", ("admin", senha_hash, 1))
        conn.commit()
    except:
        pass
    conn.close()

criar_tabelas()
criar_admin()

# =========================
# AUTH
# =========================
def verificar_senha(senha, hash):
    return bcrypt.checkpw(senha.encode(), hash.encode())

def login(user, senha):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE usuario=?", (user,))
    r = c.fetchone()
    conn.close()
    if r and verificar_senha(senha, r[2]):
        return r
    return None

def criar_usuario(user, senha):
    conn = connect()
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
    try:
        conn.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?)", (user, senha_hash, 0))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

# =========================
# SESSION
# =========================
if "logado" not in st.session_state:
    st.session_state["logado"] = False

# =========================
# LOGIN + CADASTRO
# =========================
if not st.session_state["logado"]:

    st.markdown("""
    <div style="text-align:center;">
        <img src="https://www.duartegestao.com.br/images/logo-duartegestao.png" width="200">
    </div>
    """, unsafe_allow_html=True)

    abas = st.tabs(["Login", "Criar Conta"])

    with abas[0]:
        user = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")

        if st.button("Entrar"):
            r = login(user, senha)
            if r:
                st.session_state["logado"] = True
                st.session_state["usuario"] = r[1]
                st.session_state["admin"] = r[3]
                st.rerun()
            else:
                st.error("Erro login")

    with abas[1]:
        novo_user = st.text_input("Novo usuário")
        nova_senha = st.text_input("Senha", type="password")

        if st.button("Criar Conta"):
            if criar_usuario(novo_user, nova_senha):
                st.success("Conta criada!")
            else:
                st.error("Usuário já existe")

    st.stop()

# =========================
# SIDEBAR
# =========================
menu = st.sidebar.radio("Menu", ["Dashboard", "Despesas", "Reembolsos"])

if st.sidebar.button("Sair"):
    st.session_state["logado"] = False
    st.rerun()

# =========================
# LISTAS
# =========================
categorias = [
"Limpeza","Remuneração Sócios","Alimentação","Telefonia e Internet",
"Software e Licenças","Transportes / Logística","Material de Escritório",
"Equipamentos de Informática","Estacionamento","Móveis e Utensílios",
"Despesas de Viagens","Máquinas e Equipamentos"
]

centros = [
"Credenciamento","Rede","Diretoria","Duarte Gestão","Marketing","Financeiro"
]

# =========================
# DASHBOARD
# =========================
if menu == "Dashboard":

    st.markdown('<div class="title">📊 Dashboard</div>', unsafe_allow_html=True)

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    st.metric("Total", f"R$ {df['valor'].sum() if not df.empty else 0:.2f}")

    if not df.empty:
        st.plotly_chart(px.pie(df, names="categoria", values="valor"))
        st.plotly_chart(px.bar(df, x="centro_custo", y="valor"))

        st.markdown("## 📊 Centro de Custos (Análise)")
        st.plotly_chart(px.pie(df, names="centro_custo", values="valor"))
        st.plotly_chart(px.bar(df, x="centro_custo", y="valor"))

    conn.close()

# =========================
# DESPESAS
# =========================
elif menu == "Despesas":

    tab1, tab2 = st.tabs(["Nova", "Minhas"])

    conn = connect()

    # NOVA
    with tab1:
        desc = st.text_input("Descrição")
        valor = st.number_input("Valor", min_value=0.0)
        categoria = st.selectbox("Categoria", categorias)
        centro = st.selectbox("Centro de Custo", centros)
        arquivos = st.file_uploader("Nota", accept_multiple_files=True)

        if st.button("Enviar"):
            paths = []
            for arq in arquivos:
                p = f"uploads/{arq.name}"
                with open(p, "wb") as f:
                    f.write(arq.read())
                paths.append(p)

            conn.execute("""
            INSERT INTO despesas (usuario, descricao, categoria, centro_custo, valor, arquivos)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (st.session_state["usuario"], desc, categoria, centro, valor, ",".join(paths)))

            conn.commit()
            st.success("Enviado!")

    # MINHAS
    with tab2:
        df = pd.read_sql(f"SELECT * FROM despesas WHERE usuario='{st.session_state['usuario']}'", conn)

        for i, row in df.iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)

            st.write(f"💰 {row['valor']} | {row['status']}")
            st.write(row["descricao"])

            if st.button("Excluir", key=f"del{i}"):
                conn.execute("DELETE FROM despesas WHERE id=?", (row["id"],))
                conn.commit()
                st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

    conn.close()

# =========================
# REEMBOLSOS
# =========================
elif menu == "Reembolsos":

    if not st.session_state.get("admin"):
        st.error("Apenas admin")
        st.stop()

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    for i, row in df.iterrows():
        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.write(f"{row['usuario']} | {row['valor']} | {row['status']}")

        nova_cat = st.selectbox("Categoria", categorias, key=f"cat{i}")
        novo_centro = st.selectbox("Centro", centros, key=f"cent{i}")
        novo_valor = st.number_input("Valor", value=row["valor"], key=f"val{i}")

        if st.button("Salvar", key=f"save{i}"):
            conn.execute("""
            UPDATE despesas SET categoria=?, centro_custo=?, valor=? WHERE id=?
            """, (nova_cat, novo_centro, novo_valor, row["id"]))
            conn.commit()
            st.success("Atualizado")

        col1, col2, col3 = st.columns(3)

        if col1.button("Aprovar", key=f"a{i}"):
            conn.execute("UPDATE despesas SET status='APROVADO', data_aprovacao=? WHERE id=?",
                         (datetime.now(), row["id"]))

        if col2.button("Pagar", key=f"p{i}"):
            conn.execute("UPDATE despesas SET status='PAGO', data_pagamento=? WHERE id=?",
                         (datetime.now(), row["id"]))

        if col3.button("Rejeitar", key=f"r{i}"):
            conn.execute("UPDATE despesas SET status='REJEITADO' WHERE id=?",
                         (row["id"],))

        conn.commit()

        st.markdown('</div>', unsafe_allow_html=True)

    conn.close()