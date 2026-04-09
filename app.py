import streamlit as st
import sqlite3
import os
import pandas as pd
import plotly.express as px
import bcrypt
from datetime import datetime
import time

st.set_page_config(page_title="Duarte Gestão", layout="wide")

# =========================
# 🎨 UI PROFISSIONAL + ANIMAÇÕES
# =========================
st.markdown("""
<style>
body {
    background: linear-gradient(135deg,#0f172a,#020617);
    color:#e2e8f0;
}

/* Cards */
.card {
    background: #111827;
    padding:20px;
    border-radius:15px;
    margin-bottom:15px;
    border:1px solid #1f2937;
    transition: 0.3s;
    animation: fadeUp 0.5s ease-in-out;
}
.card:hover {
    transform: translateY(-5px);
    box-shadow: 0 0 20px rgba(0,0,0,0.5);
}

/* Título */
.title {
    font-size:28px;
    font-weight:bold;
    margin-bottom:15px;
}

/* Animação */
@keyframes fadeUp {
    from {opacity:0; transform:translateY(20px);}
    to {opacity:1; transform:translateY(0);}
}

/* Botões */
.stButton>button {
    background: linear-gradient(90deg,#2563eb,#3b82f6);
    color:white;
    border-radius:10px;
    border:none;
    padding:8px 15px;
    transition:0.3s;
}
.stButton>button:hover {
    transform:scale(1.05);
    background: linear-gradient(90deg,#1d4ed8,#2563eb);
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
# LOGIN
# =========================
if not st.session_state["logado"]:

    st.markdown("""
    <div style="text-align:center; animation:fadeUp 1s;">
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
            with st.spinner("Entrando..."):
                time.sleep(1)
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
            with st.spinner("Criando..."):
                time.sleep(1)
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

menu = st.sidebar.radio("Menu", ["Dashboard", "Despesas", "Reembolsos", "Relatórios"])

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
        df["data_criacao"] = pd.to_datetime(df["data_criacao"])
        df["mes"] = df["data_criacao"].dt.to_period("M").astype(str)

        st.plotly_chart(px.line(df.groupby("mes")["valor"].sum().reset_index(),
                               x="mes", y="valor"), use_container_width=True)

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
        categoria = st.selectbox("Categoria", ["Alimentação","Transporte","Outros"])
        arquivos = st.file_uploader("Nota", accept_multiple_files=True)

        if st.button("Enviar"):
            with st.spinner("Salvando..."):
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
# REEMBOLSOS
# =========================
elif menu == "Reembolsos":

    if not st.session_state.get("admin"):
        st.error("Apenas admin")
        st.stop()

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    for _, row in df.iterrows():
        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.write(f"{row['usuario']} | R$ {row['valor']} | {row['status']}")

        if row["arquivos"]:
            arquivos = row["arquivos"].split(",")
            for i, arq in enumerate(arquivos):
                if os.path.exists(arq):
                    if arq.endswith((".png",".jpg",".jpeg")):
                        st.image(arq)
                    elif arq.endswith(".pdf"):
                        with open(arq, "rb") as f:
                            st.download_button("Abrir PDF", f,
                                file_name=os.path.basename(arq),
                                key=f"admin_pdf_{row['id']}_{i}")

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

# =========================
# RELATÓRIOS
# =========================
elif menu == "Relatórios":

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    st.dataframe(df)

    st.download_button("Baixar CSV",
                       df.to_csv(index=False),
                       "relatorio.csv")

    conn.close()