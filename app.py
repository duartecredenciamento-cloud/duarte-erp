import streamlit as st
import sqlite3
import os
import pandas as pd
import plotly.express as px
import bcrypt
from datetime import datetime

st.set_page_config(page_title="Duarte Gestão", layout="wide")

# =========================
# 🎨 ESTILO
# =========================
st.markdown("""
<style>
body {background: linear-gradient(135deg,#0f172a,#020617);color:#e2e8f0;}
.card {
    background: linear-gradient(145deg,#1e293b,#0f172a);
    padding:20px;
    border-radius:15px;
    margin-bottom:15px;
    box-shadow: 0 0 25px rgba(0,0,0,0.4);
}
.title {font-size:30px;font-weight:bold;}
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
    c = conn.cursor()
    senha_hash = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()

    try:
        c.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?)", ("admin", senha_hash, 1))
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
    result = c.fetchone()
    conn.close()

    if result and verificar_senha(senha, result[2]):
        return result
    return None

def criar_usuario(user, senha):
    conn = connect()
    c = conn.cursor()
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

    try:
        c.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?)", (user, senha_hash, 0))
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
# LOGIN
# =========================
if not st.session_state["logado"]:

    st.markdown("""
    <div style="text-align:center;">
        <a href="https://www.duartegestao.com.br/index.html" target="_blank">
            <img src="https://www.duartegestao.com.br/images/logo-duartegestao.png" width="220">
        </a>
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
                st.error("Erro no login")

    with abas[1]:
        u = st.text_input("Novo usuário")
        s = st.text_input("Nova senha", type="password")

        if st.button("Criar Conta"):
            if criar_usuario(u, s):
                st.success("Conta criada!")
            else:
                st.error("Usuário já existe")

    st.stop()

# =========================
# SIDEBAR
# =========================
st.sidebar.markdown("""
<a href="https://www.duartegestao.com.br/index.html" target="_blank">
    <img src="https://www.duartegestao.com.br/images/logo-duartegestao.png" width="180">
</a>
""", unsafe_allow_html=True)

menu = st.sidebar.radio("Menu", ["Dashboard", "Despesas", "Reembolsos"])

if st.sidebar.button("Sair"):
    st.session_state["logado"] = False
    st.rerun()

# =========================
# DASHBOARD
# =========================
if menu == "Dashboard":

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    st.markdown('<div class="title">📊 Dashboard</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total", f"R$ {df['valor'].sum() if not df.empty else 0:.2f}")
    col2.metric("Qtde", len(df))
    col3.metric("Média", f"R$ {df['valor'].mean() if not df.empty else 0:.2f}")

    if not df.empty:
        st.plotly_chart(px.bar(df, x="usuario", y="valor"), use_container_width=True)

    conn.close()

# =========================
# DESPESAS
# =========================
elif menu == "Despesas":

    conn = connect()

    tab1, tab2 = st.tabs(["Nova", "Minhas"])

    with tab1:
        desc = st.text_input("Descrição")
        valor = st.number_input("Valor", min_value=0.0)
        categoria = st.selectbox("Categoria", ["Alimentação", "Transporte", "Outros"])
        arquivos = st.file_uploader("Nota", accept_multiple_files=True)

        if st.button("Enviar"):
            lista = []
            for arq in arquivos:
                path = f"uploads/{arq.name}"
                with open(path, "wb") as f:
                    f.write(arq.read())
                lista.append(path)

            conn.execute("""
            INSERT INTO despesas (usuario, descricao, categoria, valor, arquivos)
            VALUES (?, ?, ?, ?, ?)
            """, (st.session_state["usuario"], desc, categoria, valor, ",".join(lista)))

            conn.commit()
            st.success("Enviado!")

    with tab2:
        df = pd.read_sql(f"SELECT * FROM despesas WHERE usuario='{st.session_state['usuario']}'", conn)

        for _, row in df.iterrows():

            st.markdown('<div class="card">', unsafe_allow_html=True)

            st.write(f"R$ {row['valor']} | {row['status']}")
            st.write(row["descricao"])

            if row["arquivos"]:
                arquivos = row["arquivos"].split(",")
                for i, arq in enumerate(arquivos):
                    if os.path.exists(arq):
                        if arq.endswith((".png",".jpg",".jpeg")):
                            st.image(arq)
                        elif arq.endswith(".pdf"):
                            with open(arq, "rb") as f:
                                st.download_button("PDF", f,
                                    file_name=os.path.basename(arq),
                                    key=f"user_pdf_{row['id']}_{i}")

            if st.button("Excluir", key=f"del_{row['id']}"):
                conn.execute("DELETE FROM despesas WHERE id=?", (row['id'],))
                conn.commit()
                st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

    conn.close()

# =========================
# REEMBOLSOS TOP
# =========================
elif menu == "Reembolsos":

    if not st.session_state.get("admin"):
        st.error("Apenas admin")
        st.stop()

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    # 🔥 FILTROS COMPLETOS
    col1, col2, col3 = st.columns(3)

    user = col1.selectbox("Funcionário", ["Todos"] + list(df["usuario"].unique()))
    status = col2.selectbox("Status", ["Todos","PENDENTE","APROVADO","PAGO","REJEITADO"])
    periodo = col3.date_input("Período", [])

    if user != "Todos":
        df = df[df["usuario"] == user]

    if status != "Todos":
        df = df[df["status"] == status]

    if len(periodo) == 2:
        df["data_criacao"] = pd.to_datetime(df["data_criacao"])
        df = df[(df["data_criacao"] >= str(periodo[0])) & (df["data_criacao"] <= str(periodo[1]))]

    st.metric("Total filtrado", f"R$ {df['valor'].sum() if not df.empty else 0:.2f}")

    for _, row in df.iterrows():

        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.write(f"{row['usuario']} | R$ {row['valor']} | {row['status']}")

        # 🔥 PREVIEW DIRETO
        if row["arquivos"]:
            arquivos = row["arquivos"].split(",")

            for arq in arquivos:
                if os.path.exists(arq):
                    if arq.endswith((".png",".jpg",".jpeg")):
                        st.image(arq)
                    elif arq.endswith(".pdf"):
                        with open(arq, "rb") as f:
                            st.download_button("Abrir PDF", f,
                                file_name=os.path.basename(arq),
                                key=f"pdf_admin_{row['id']}")

        col1, col2, col3 = st.columns(3)

        if col1.button("Aprovar", key=f"a_{row['id']}"):
            conn.execute("UPDATE despesas SET status='APROVADO', data_aprovacao=? WHERE id=?",
                         (datetime.now(),row['id']))

        if col2.button("Pagar", key=f"p_{row['id']}"):
            conn.execute("UPDATE despesas SET status='PAGO', data_pagamento=? WHERE id=?",
                         (datetime.now(),row['id']))

        if col3.button("Rejeitar", key=f"r_{row['id']}"):
            conn.execute("UPDATE despesas SET status='REJEITADO' WHERE id=?",(row['id'],))

        st.markdown('</div>', unsafe_allow_html=True)

    conn.commit()
    conn.close()