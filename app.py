import streamlit as st
import sqlite3
import os
import pandas as pd
import plotly.express as px
import bcrypt

st.set_page_config(page_title="Duarte Gestão", layout="wide")

# =========================
# 🎨 ESTILO
# =========================
st.markdown("""
<style>
body {background-color:#0f172a;color:#e2e8f0;}
section[data-testid="stSidebar"] {background-color:#020617;}
.card {
    background: linear-gradient(145deg,#1e293b,#0f172a);
    padding:20px;
    border-radius:15px;
    margin-bottom:15px;
}
.title {
    font-size:30px;
    font-weight:bold;
}
</style>
""", unsafe_allow_html=True)

# =========================
# SESSION
# =========================
if "logado" not in st.session_state:
    st.session_state["logado"] = False

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
        status TEXT DEFAULT 'PENDENTE'
    )
    """)

    conn.commit()
    conn.close()

criar_tabelas()

# =========================
# AUTH
# =========================
def hash_senha(senha):
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt())

def verificar_senha(senha, hash):
    return bcrypt.checkpw(senha.encode(), hash)

def login(user, senha):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE usuario=?", (user,))
    result = c.fetchone()
    conn.close()

    if result:
        if verificar_senha(senha, result[2].encode()):
            return result
    return None

def criar_usuario(user, senha, admin):
    conn = connect()
    c = conn.cursor()
    senha_hash = hash_senha(senha)

    try:
        c.execute("INSERT INTO usuarios VALUES (NULL, ?, ?, ?)", (user, senha_hash.decode(), admin))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

# =========================
# 🔐 LOGIN
# =========================
if not st.session_state["logado"]:

    st.markdown("""
    <div style="text-align:center;">
        <a href="https://www.duartegestao.com.br/index.html" target="_blank">
            <img src="https://www.duartegestao.com.br/images/logo-duartegestao.png" width="220">
        </a>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="title" style="text-align:center;">Sistema de Despesas</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        user = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")

        if st.button("Entrar"):
            result = login(user, senha)

            if result:
                st.session_state["logado"] = True
                st.session_state["usuario"] = result[1]
                st.session_state["admin"] = result[3]
                st.rerun()
            else:
                st.error("Login inválido")

    st.stop()

# =========================
# MENU
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

    st.markdown('<div class="title">📊 Dashboard</div>', unsafe_allow_html=True)

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    col1, col2 = st.columns(2)

    total = df["valor"].sum() if not df.empty else 0

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

    tab1, tab2 = st.tabs(["Nova", "Minhas"])

    # NOVA
    with tab1:
        desc = st.text_input("Descrição")
        categoria = st.selectbox("Categoria", ["Alimentação", "Transporte", "Hospedagem", "Outros"])
        valor = st.number_input("Valor", min_value=0.0)
        arquivos = st.file_uploader("Nota", accept_multiple_files=True)

        if st.button("Salvar"):
            lista = []

            for arquivo in arquivos:
                caminho = f"uploads/{arquivo.name}"
                with open(caminho, "wb") as f:
                    f.write(arquivo.read())
                lista.append(caminho)

            conn = connect()
            conn.execute("""
            INSERT INTO despesas (usuario, descricao, categoria, valor, arquivos)
            VALUES (?, ?, ?, ?, ?)
            """, (st.session_state["usuario"], desc, categoria, valor, ",".join(lista)))

            conn.commit()
            conn.close()

            st.success("Despesa enviada!")

    # MINHAS
    with tab2:
        conn = connect()
        df = pd.read_sql(f"SELECT * FROM despesas WHERE usuario='{st.session_state['usuario']}'", conn)

        st.dataframe(df)

        for i, row in df.iterrows():
            if row["arquivos"]:
                arquivos = row["arquivos"].split(",")

                for arq in arquivos:
                    if os.path.exists(arq):
                        if arq.lower().endswith((".png", ".jpg", ".jpeg")):
                            st.image(arq, width=200)
                        elif arq.lower().endswith(".pdf"):
                            with open(arq, "rb") as f:
                                st.download_button("Abrir PDF", f, file_name=os.path.basename(arq))

        conn.close()

# =========================
# REEMBOLSOS (ADMIN)
# =========================
elif menu == "Reembolsos":

    if not st.session_state.get("admin"):
        st.stop()

    st.markdown('<div class="title">💰 Reembolsos</div>', unsafe_allow_html=True)

    conn = connect()
    df = pd.read_sql("SELECT * FROM despesas", conn)

    # FILTROS
    col1, col2 = st.columns(2)

    user_filtro = col1.selectbox("Funcionário", ["Todos"] + list(df["usuario"].unique()))
    status_filtro = col2.selectbox("Status", ["Todos", "PENDENTE", "APROVADO", "PAGO", "REJEITADO"])

    if user_filtro != "Todos":
        df = df[df["usuario"] == user_filtro]

    if status_filtro != "Todos":
        df = df[df["status"] == status_filtro]

    total = df["valor"].sum()

    st.metric("Total filtrado", f"R$ {total:.2f}")

    for i, row in df.iterrows():

        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.write(f"👤 {row['usuario']} | 💰 R$ {row['valor']} | 📌 {row['status']}")

        if row["arquivos"]:
            arquivos = row["arquivos"].split(",")

            for arq in arquivos:
                if os.path.exists(arq):
                    if arq.lower().endswith((".png", ".jpg", ".jpeg")):
                        st.image(arq, width=200)
                    elif arq.lower().endswith(".pdf"):
                        with open(arq, "rb") as f:
                            st.download_button("Abrir PDF", f, file_name=os.path.basename(arq))

        col1, col2, col3 = st.columns(3)

        if col1.button(f"Aprovar {row['id']}"):
            conn.execute("UPDATE despesas SET status='APROVADO' WHERE id=?", (row['id'],))

        if col2.button(f"Pagar {row['id']}"):
            conn.execute("UPDATE despesas SET status='PAGO' WHERE id=?", (row['id'],))

        if col3.button(f"Rejeitar {row['id']}"):
            conn.execute("UPDATE despesas SET status='REJEITADO' WHERE id=?", (row['id'],))

        st.markdown('</div>', unsafe_allow_html=True)

    conn.commit()
    conn.close()