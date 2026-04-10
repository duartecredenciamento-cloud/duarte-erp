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
}
.title {
    font-size:28px;
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
        nome TEXT,
        email TEXT,
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
        centro TEXT,
        valor REAL,
        arquivos TEXT,
        status TEXT DEFAULT 'PENDENTE',
        data_criacao TEXT,
        data_aprovacao TEXT,
        data_pagamento TEXT
    )
    """)

    conn.commit()
    conn.close()

def criar_admin():
    conn = connect()
    c = conn.cursor()

    senha_hash = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()

    try:
        c.execute("INSERT INTO usuarios VALUES (NULL,?,?,?,?,?)",
                  ("Admin","admin@email.com","admin",senha_hash,1))
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

    if r and verificar_senha(senha, r[4]):
        return r
    return None

def criar_usuario(nome,email,user,senha):
    conn = connect()
    c = conn.cursor()
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

    try:
        c.execute("INSERT INTO usuarios VALUES (NULL,?,?,?,?,?)",
                  (nome,email,user,senha_hash,0))
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
# LOGIN / CADASTRO
# =========================
if not st.session_state["logado"]:

    abas = st.tabs(["Login","Criar Conta"])

    # LOGIN
    with abas[0]:
        user = st.text_input("Usuário", key="login_user")
        senha = st.text_input("Senha", type="password", key="login_senha")

        if st.button("Entrar"):
            r = login(user, senha)
            if r:
                st.session_state["logado"] = True
                st.session_state["usuario"] = r[3]
                st.session_state["admin"] = r[5]
                st.rerun()
            else:
                st.error("Login inválido")

    # CADASTRO
    with abas[1]:
        nome = st.text_input("Nome completo", key="cad_nome")
        email = st.text_input("Email", key="cad_email")
        user = st.text_input("Usuário", key="cad_user")
        senha = st.text_input("Senha", type="password", key="cad_senha")

        if st.button("Criar Conta"):
            if criar_usuario(nome,email,user,senha):
                st.success("Conta criada!")
            else:
                st.error("Usuário já existe")

    st.stop()

# =========================
# MENU
# =========================
menu = st.sidebar.radio("Menu", ["Dashboard","Despesas","Reembolsos"])

if st.sidebar.button("Sair"):
    st.session_state["logado"] = False
    st.rerun()

# =========================
# DASHBOARD
# =========================
if menu == "Dashboard":

    st.markdown('<div class="title">📊 Dashboard</div>', unsafe_allow_html=True)

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    if not df.empty:
        st.metric("Total", f"R$ {df['valor'].sum():.2f}")

        st.plotly_chart(px.pie(df, names="categoria", values="valor"))
        st.plotly_chart(px.bar(df, x="centro", y="valor"))

    conn.close()

# =========================
# DESPESAS
# =========================
elif menu == "Despesas":

    tab1, tab2 = st.tabs(["Nova","Minhas"])

    # NOVA
    with tab1:
        desc = st.text_input("Descrição", key="desc")
        valor = st.number_input("Valor", key="valor")
        categoria = st.selectbox("Categoria",
            ["Limpeza","Alimentação","Software","Transporte"])
        centro = st.selectbox("Centro",
            ["FINANCEIRO","MARKETING","DIRETORIA","REDE"])

        arquivos = st.file_uploader("Arquivos", accept_multiple_files=True, key="upload")

        if st.button("Enviar"):
            lista = []
            for arq in arquivos:
                path = f"uploads/{arq.name}"
                with open(path,"wb") as f:
                    f.write(arq.read())
                lista.append(path)

            conn = connect()
            conn.execute("""
            INSERT INTO despesas VALUES (NULL,?,?,?,?,?,?,?,?,?,?)
            """,(st.session_state["usuario"],desc,categoria,centro,valor,
                 ",".join(lista),"PENDENTE",datetime.now(),None,None))
            conn.commit()
            conn.close()

            st.success("Enviado!")

    # MINHAS
    with tab2:
        conn = connect()
        df = pd.read_sql(f"""
        SELECT * FROM despesas WHERE usuario='{st.session_state["usuario"]}'
        """, conn)

        for _,row in df.iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)

            st.write(row["descricao"], row["valor"], row["status"])

            # ARQUIVOS
            if row["arquivos"]:
                for i,arq in enumerate(row["arquivos"].split(",")):
                    if os.path.exists(arq):
                        if arq.endswith(".pdf"):
                            with open(arq,"rb") as f:
                                st.download_button("PDF", f,
                                    file_name=os.path.basename(arq),
                                    key=f"pdf_{row['id']}_{i}")
                        else:
                            st.image(arq)

            # EXCLUIR
            if st.button("Excluir", key=f"del_{row['id']}"):
                conn.execute("DELETE FROM despesas WHERE id=?", (row["id"],))
                conn.commit()
                st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

        conn.close()

# =========================
# REEMBOLSOS
# =========================
elif menu == "Reembolsos":

    if not st.session_state["admin"]:
        st.error("Apenas admin")
        st.stop()

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    for _,row in df.iterrows():

        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.write(row["usuario"], row["valor"], row["status"])

        # PREVIEW
        if row["arquivos"]:
            for i,arq in enumerate(row["arquivos"].split(",")):
                if os.path.exists(arq):
                    if arq.endswith(".pdf"):
                        with open(arq,"rb") as f:
                            st.download_button("PDF", f,
                                file_name=os.path.basename(arq),
                                key=f"adm_pdf_{row['id']}_{i}")
                    else:
                        st.image(arq)

        col1,col2,col3 = st.columns(3)

        if col1.button("Aprovar", key=f"ap_{row['id']}"):
            conn.execute("UPDATE despesas SET status='APROVADO', data_aprovacao=? WHERE id=?",
                         (datetime.now(), row["id"]))

        if col2.button("Pagar", key=f"pg_{row['id']}"):
            conn.execute("UPDATE despesas SET status='PAGO', data_pagamento=? WHERE id=?",
                         (datetime.now(), row["id"]))

        if col3.button("Rejeitar", key=f"rj_{row['id']}"):
            conn.execute("UPDATE despesas SET status='REJEITADO' WHERE id=?",
                         (row["id"],))

        st.markdown('</div>', unsafe_allow_html=True)

    conn.commit()
    conn.close()