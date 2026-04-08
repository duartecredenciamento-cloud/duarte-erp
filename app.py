import streamlit as st
import sqlite3
import os
import pandas as pd
import plotly.express as px
import bcrypt
from datetime import datetime

st.set_page_config(page_title="Duarte Gestão", layout="wide")

# =========================
# 🎨 ESTILO TOP
# =========================
st.markdown("""
<style>
body {
    background: linear-gradient(135deg,#0f172a,#020617);
    color: #e2e8f0;
}
.card {
    background: linear-gradient(145deg,#1e293b,#0f172a);
    padding:20px;
    border-radius:15px;
    margin-bottom:15px;
    box-shadow: 0 0 20px rgba(0,0,0,0.3);
    animation: fadeIn 0.5s ease-in;
}
@keyframes fadeIn {
    from {opacity:0; transform:translateY(10px);}
    to {opacity:1; transform:translateY(0);}
}
.title {
    font-size:30px;
    font-weight:bold;
}
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
# 🔐 LOGIN MODERNO
# =========================
if not st.session_state["logado"]:

    st.markdown("""
    <div style="text-align:center;">
        <a href="https://www.duartegestao.com.br/index.html" target="_blank">
            <img src="https://www.duartegestao.com.br/images/logo-duartegestao.png" width="220">
        </a>
    </div>
    """, unsafe_allow_html=True)

    abas = st.tabs(["🔐 Login", "📝 Criar Conta"])

    with abas[0]:
        user = st.text_input("Usuário", key="login_user")
        senha = st.text_input("Senha", type="password", key="login_senha")

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
        u = st.text_input("Novo usuário", key="novo_user")
        s = st.text_input("Nova senha", type="password", key="nova_senha")

        if st.button("Criar Conta"):
            if criar_usuario(u, s):
                st.success("Conta criada!")
            else:
                st.error("Usuário já existe")

    st.stop()

# =========================
# SIDEBAR COM LOGO
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
# DASHBOARD TOP
# =========================
if menu == "Dashboard":

    st.markdown('<div class="title">📊 Dashboard</div>', unsafe_allow_html=True)

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    total = df["valor"].sum() if not df.empty else 0

    col1, col2 = st.columns(2)
    col1.metric("💰 Total", f"R$ {total:.2f}")
    col2.metric("📄 Quantidade", len(df))

    if not df.empty:
        st.plotly_chart(px.pie(df, names="categoria", values="valor"), use_container_width=True)
        st.plotly_chart(px.bar(df, x="usuario", y="valor"), use_container_width=True)

    conn.close()

# =========================
# DESPESAS
# =========================
elif menu == "Despesas":

    st.markdown('<div class="title">💳 Nova Despesa</div>', unsafe_allow_html=True)

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

        conn = connect()
        conn.execute("""
        INSERT INTO despesas (usuario, descricao, categoria, valor, arquivos)
        VALUES (?, ?, ?, ?, ?)
        """, (st.session_state["usuario"], desc, categoria, valor, ",".join(lista)))

        conn.commit()
        conn.close()

        st.success("Despesa enviada!")

# =========================
# REEMBOLSOS
# =========================
elif menu == "Reembolsos":

    if not st.session_state.get("admin"):
        st.error("Apenas admin")
        st.stop()

    st.markdown('<div class="title">💰 Reembolsos</div>', unsafe_allow_html=True)

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    for _, row in df.iterrows():

        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.write(f"👤 {row['usuario']} | 💰 {row['valor']} | {row['status']}")
        st.write(f"📅 Criado: {row['data_criacao']}")
        st.write(f"✔ Aprovado: {row['data_aprovacao']}")
        st.write(f"💸 Pago: {row['data_pagamento']}")

        col1, col2, col3 = st.columns(3)

        if col1.button(f"Aprovar {row['id']}"):
            conn.execute("UPDATE despesas SET status='APROVADO', data_aprovacao=? WHERE id=?",
                         (datetime.now(), row['id']))

        if col2.button(f"Pagar {row['id']}"):
            conn.execute("UPDATE despesas SET status='PAGO', data_pagamento=? WHERE id=?",
                         (datetime.now(), row['id']))

        if col3.button(f"Rejeitar {row['id']}"):
            conn.execute("UPDATE despesas SET status='REJEITADO' WHERE id=?",
                         (row['id'],))

        st.markdown('</div>', unsafe_allow_html=True)

    conn.commit()
    conn.close()