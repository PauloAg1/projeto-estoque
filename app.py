import os
from functools import wraps
from decimal import Decimal, InvalidOperation
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, url_for

from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user
)

from werkzeug.security import check_password_hash, generate_password_hash

from db import get_connection

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")

login_manager = LoginManager(app)
login_manager.login_view = "login" # type: ignore
login_manager.login_message = "Faça login para acessar o sistema."
login_manager.login_message_category = "warning"


# --------- Usuário (Para o Flask-Login) --------- #

class Usuario(UserMixin):
    def __init__(self, id, nome, usuario, senha_hash, perfil, ativo):
        self.id = id
        self.nome = nome
        self.usuario = usuario
        self.senha_hash = senha_hash
        self.perfil = perfil
        self.ativo = ativo

    @property
    def is_active(self): # type: ignore[override]
        return bool(self.ativo)

    @property
    def is_authenticated(self): # type: ignore[override]
        return bool(self.ativo)

    @property
    def is_admin(self):
        return self.perfil == "admin"


def buscar_usuario_por_id(usuario_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, nome, usuario, senha_hash, perfil, ativo "
                "FROM usuarios WHERE id = %s",
                (usuario_id,)
            
            )
            return cursor.fetchone()
    finally:
        conn.close()


@login_manager.user_loader
def carregar_usuario(usuario_id):
    linha = buscar_usuario_por_id(usuario_id)
    return Usuario(**linha) if linha else None


def admin_obrigatorio(funcao):
    @wraps(funcao)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            flash("Apenas administradores podem acessar essa página.", "danger")
            return redirect(url_for("inicio"))
        return(funcao(*args, **kwargs))

    return wrapper


# --------- Rotas --------- #

@app.route("/")
@login_required
def inicio():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM produtos "
                "WHERE estoque_minimo > 0 AND quantidade <= estoque_minimo"
            )
            em_alerta = cursor.fetchone()["total"]
    finally:
        conn.close()
    return render_template("inicio.html", em_alerta=em_alerta)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("inicio"))

    if request.method == "POST":
        nome_login = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, nome, usuario, senha_hash, perfil, ativo "
                    "FROM usuarios WHERE usuario = %s",
                    (nome_login,),
                )
                linha = cursor.fetchone()
        finally:
            conn.close()


        if linha is None or not check_password_hash(linha["senha_hash"], senha):
            flash("Usuário ou senha inválidos.", "danger")
        elif not linha["ativo"]:
            flash("Este usuário está desativado.", "danger")
        else:
            login_user(Usuario(**linha))
            flash(f"Bem-vindo(a), {linha['nome']}!", "success")
            return redirect(url_for("inicio"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sessão encerrada.", "success")
    return redirect(url_for("login"))


@app.route("/usuarios")
@login_required
@admin_obrigatorio
def listar_usuarios():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, nome, usuario, perfil, ativo FROM usuarios ORDER BY nome"
            )
            usuarios = cursor.fetchall()
    finally:
        conn.close()
    return render_template("usuarios.html", usuarios = usuarios)


@app.route("/usuarios/novo", methods=["GET", "POST"])
@login_required
@admin_obrigatorio
def novo_usuario():
    valores = {"nome": "", "usuario": "", "perfil": "funcionario"}

    if request.method == "POST":
        valores["nome"] = request.form.get("nome", "").strip()
        valores["usuario"] = request.form.get("usuario", "").strip()
        valores["perfil"] = request.form.get("perfil", "funcionario")
        senha = request.form.get("senha", "")

        erros = []
        if not valores["nome"]:
            erros.append("Informe o nome completo.")
        if not valores["usuario"]:
            erros.append("Informe o nome de usuario para login.")
        if len(senha) < 6:
            erros.append("A senha deve ter pelo menos 6 caracteres.")
        if valores["perfil"] not in ["admin", "funcionario"]:
            erros.append("Perfil inválido.")

        if not erros:
            conn = get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM usuarios WHERE usuario = %s",
                        (valores["usuario"],)
                    )
                    if cursor.fetchone():
                        erros.append("Ja existe um usuário com esse login.")
                    else:
                        cursor.execute(
                            "INSERT INTO usuarios (nome, usuario, senha_hash, perfil) "
                            "VALUES (%s, %s, %s, %s)",
                            (
                                valores["nome"],
                                valores["usuario"],
                                generate_password_hash(senha),
                                valores["perfil"]
                            ),
                        )
                conn.commit()
            finally:
                conn.close()

        if erros:
            for erro in erros:
                flash(erro, "danger")
            return render_template("usuario_form.html", modo_edicao=False, valores = valores)

        flash(f"Usuário {valores['nome']} criado com sucesso.", "success")
        return redirect(url_for("listar_usuarios"))

    return render_template("usuario_form.html", modo_edicao=False, valores = valores)


@app.route("/usuarios/<int:usuario_id>/editar", methods=["GET", "POST"])
@login_required
@admin_obrigatorio
def editar_usuario(usuario_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, nome, usuario, perfil FROM usuarios WHERE id = %s",
                (usuario_id, )
            )
            usuario_edicao = cursor.fetchone()
    finally:
        conn.close()

    if usuario_edicao is None:
        flash("Usuário não encontrado.", "danger")
        return redirect(url_for("listar_usuarios"))

    valores = {
        "nome": usuario_edicao["nome"],
        "usuario": usuario_edicao["usuario"],
        "perfil": usuario_edicao["perfil"],
    }

    if request.method == "POST":
        valores["nome"] = request.form.get("nome", "").strip()
        valores["usuario"] = request.form.get("usuario", "").strip()
        valores["perfil"] = request.form.get("perfil", "funcionario").strip()
        nova_senha = request.form.get("senha", "")

        erros = []
        if not valores["nome"]:
            erros.append("Informe o nome completo.")
        if not valores["usuario"]:
            erros.append("Informe o nome de usuário para login.")
        if nova_senha and len(nova_senha) < 6:
            erros.append("A senha deve ter pelo menos 6 caracteres.")
        if valores["perfil"] not in ["admin", "funcionario"]:
            erros.append("Perfil inválido.")
        if usuario_id == current_user.id and valores["perfil"] != "admin":
            erros.append("Você não pode remover seu próprio cargo de administrador.")

        if not erros:
            conn = get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM usuarios WHERE usuario = %s AND id <> %s",
                        (valores["usuario"], usuario_id)
                    )

                    if cursor.fetchone():
                        erros.append("Já existe outro usuario com esse login.")
                    elif nova_senha:
                        cursor.execute(
                            "UPDATE usuarios SET nome = %s, usuario = %s, perfil = %s, "
                            "senha_hash = %s WHERE id = %s",
                            (
                                valores["nome"],
                                valores["usuario"],
                                valores["perfil"],
                                generate_password_hash(nova_senha),
                                usuario_id,
                            ),
                        )
                    else:
                        cursor.execute(
                            "UPDATE usuarios SET nome = %s, usuario = %s, perfil = %s "
                            "WHERE id = %s",
                            (
                                valores["nome"],
                                valores["usuario"],
                                valores["perfil"],
                                usuario_id,
                            ),
                        )
                        conn.commit()
            finally:
                conn.close()

        if erros:
            for erro in erros:
                flash(erro, "danger")
            return render_template(
                "usuario_form.html",
                modo_edicao = True,
                usuario_id = usuario_id,
                valores = valores,
            )

        flash("Usuário atualizado com sucesso.", "success")
        return redirect(url_for("listar_usuarios"))

    return render_template(
        "usuario_form.html",
        modo_edicao = True,
        usuario_id = usuario_id,
        valores = valores,
    )


@app.route("/usuarios/<int:usuario_id>/alternar", methods=["POST"])
@login_required
@admin_obrigatorio
def alternar_usuario(usuario_id):
    if usuario_id == current_user.id:
        flash("Você não pode desativar seu próprio usuário.", "danger")
        return redirect(url_for("listar_usuarios"))

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT ativo FROM usuarios WHERE id = %s", (usuario_id,))
            linha = cursor.fetchone()
            if linha is None:
                flash("Usuário não encontrado.", "danger")
                return redirect(url_for("listar_usuarios"))

            novo_status = 0 if linha["ativo"] else 1
            cursor.execute(
                "UPDATE usuarios SET ativo = %s WHERE id = %s", (novo_status, usuario_id))

            conn.commit()
    finally:
        conn.close()

    acao = "reativado" if novo_status == 1 else "desativado"
    flash(f"Usuário {acao} com sucesso.", "success")
    return redirect(url_for("listar_usuarios"))


def converter_preco(texto):
    texto = texto.strip()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        return None
    if not valor.is_finite() or valor < 0:
        return None
    return valor


@app.route("/produtos")
@login_required
def listar_produtos():
    q = request.args.get("q", "").strip()
    alerta = request.args.get("alerta") == "1"

    condicoes, params = [], []
    if q:
        condicoes.append("(nome LIKE %s OR codigo_barras = %s OR id = %s)")
        params += [f"%{q}%", q, int(q) if q.isdigit() else -1]
    if alerta:
        condicoes.append("estoque_minimo > 0 AND quantidade <= estoque_minimo")

    sql = ("SELECT id, nome, codigo_barras, preco, quantidade, estoque_minimo "
           "FROM produtos")
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)
    sql += " ORDER BY nome"

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            produtos = cursor.fetchall()
    finally:
        conn.close()
    return render_template("produtos.html", produtos=produtos, q=q, alerta=alerta)

@app.route("/produtos/novo", methods=["GET", "POST"])
@login_required
def novo_produto():
    valores = {"nome": "", "codigo_barras": "", "preco": "",
               "quantidade": "", "estoque_minimo": ""}

    if request.method == "POST":
        for campo in valores:
            valores[campo] = request.form.get(campo, "").strip()

        preco = converter_preco(valores["preco"])
        qtd_txt = valores["quantidade"] or "0"
        min_txt = valores["estoque_minimo"] or "0"
        codigo = valores["codigo_barras"] or None

        erros = []
        if not valores["nome"]:
            erros.append("Informe o nome do produto.")
        if preco is None:
            erros.append("Preço inválido. Use o formato 12,50.")
        if not qtd_txt.isdigit():
            erros.append("A quantidade inicial deve ser um número inteiro.")
        if not min_txt.isdigit():
            erros.append("O estoque mínimo deve ser um número inteiro.")

        if not erros:
            conn = get_connection()
            try:
                with conn.cursor() as cursor:
                    if codigo:
                        cursor.execute(
                            "SELECT id FROM produtos WHERE codigo_barras = %s", (codigo,)
                        )
                        if cursor.fetchone():
                            erros.append("Já existe um produto com esse código de barras.")
                    if not erros:
                        cursor.execute(
                            "INSERT INTO produtos "
                            "(nome, codigo_barras, preco, quantidade, estoque_minimo) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (valores["nome"], codigo, preco, int(qtd_txt), int(min_txt)),
                        )
                        conn.commit()
            finally:
                conn.close()

        if erros:
            for erro in erros:
                flash(erro, "danger")
            return render_template("produtos_form.html", valores=valores)

        flash("Produto cadastrado com sucesso!", "success")
        return redirect(url_for("listar_produtos"))

    return render_template("produtos_form.html", valores=valores)


@app.route("/produtos/<int:produto_id>/editar", methods=["GET", "POST"])
@login_required
def editar_produto(produto_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            produto = buscar_produto(cursor, produto_id)
            cursor.execute(
                "SELECT COUNT(*) AS total FROM movimentacoes WHERE produto_id = %s",
                (produto_id,),
            )
            tem_movimentacao = cursor.fetchone()["total"] > 0
    finally:
        conn.close()

    if produto is None:
        flash("Produto não encontrado", "danger")
        return redirect(url_for("listar_produtos"))

    valores = {
        "nome": produto["nome"],
        "codigo_barras": produto["codigo_barras"] or "",
        "preco": str(produto["preco"]).replace(",", "."),
        "quantidade": produto["quantidade"],
        "estoque_minimo": str(produto["estoque_minimo"]),
    }

    if request.method == "POST":
        for campo in ("nome", "codigo_barras", "preco", "estoque_minimo"):
            valores[campo] = request.form.get(campo, "").strip()

        preco = converter_preco(valores["preco"]) 
        min_txt = valores["estoque_minimo"] or "0"
        codigo = valores["codigo_barras"] or None

        erros = []
        if not valores["nome"]:
            erros.append("Informe o nome do produto.")
        if preco is None:
            erros.append("Preço inválido. Use o formato 12,50.")
        if not min_txt.isdigit():
            erros.append("O estoque mínimo deve ser um número inteiro.")

        if not erros:
            conn = get_connection()
            try:
                with conn.cursor() as cursor:
                    if codigo:
                        cursor.execute(
                            "SELECT id FROM produtos WHERE codigo_barras = %s AND id <> %s",
                            (codigo, produto_id),
                        )
                        if cursor.fetchone():
                            erros.append("Já existe outro produto com esse código de barras.")
                    if not erros:
                        cursor.execute(
                            "UPDATE produtos SET nome = %s, codigo_barras = %s, preco = %s, estoque_minimo = %s " 
                            "WHERE id = %s",
                            (valores["nome"], codigo, preco, int(min_txt), produto_id)
                        )
                        conn.commit()
            finally:
                conn.close()

        if erros:
            for erro in erros:
                flash(erro, "danger")
        else:
            flash("Produto atualizado com sucesso!", "success")
            return redirect(url_for("listar_produtos"))
    return render_template(
        "produtos_form.html",
        modo_edicao=True,
        produto_id=produto_id,
        valores=valores,
        tem_movimentacao=tem_movimentacao,
    )


@app.route("/produtos/<int:produto_id>/excluir", methods=["GET", "POST"])
@login_required
@admin_obrigatorio
def excluir_produto(produto_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            produto = buscar_produto(cursor, produto_id)
            if produto is None:
                flash("Produto não encontrado.", "danger")
                return redirect(url_for("listar_produtos"))

            cursor.execute(
                "SELECT COUNT(*) AS total FROM movimentacoes WHERE produto_id = %s",
                (produto_id,),
            )
            if cursor.fetchone()["total"] > 0:
                flash(f"{produto["nome"]} não pode ser excluído porque já tem movimentações registradas.", "danger")
                return redirect(url_for("editar_produto", produto_id=produto_id))

            cursor.execute("DELETE FROM produtos WHERE id = %s", (produto_id,))
        conn.commit()
    finally:
        conn.close()
                
    flash(f"{produto['nome']} excluído com sucesso.", "success")
    return redirect(url_for("listar_produtos"))


def buscar_produto(cursor, produto_id):
    cursor.execute(
        "SELECT id, nome, codigo_barras, preco, quantidade, estoque_minimo " 
        "FROM produtos WHERE id = %s",
        (produto_id,),
    )
    return cursor.fetchone()


def registrar_movimentacao(tipo):
    
    # Registrar (POST)
    if request.method == "POST":
        produto_id = request.form.get("produto_id", "")
        qtd_txt = request.form.get("quantidade", "")

        if not produto_id.isdigit() or not qtd_txt.isdigit() or int(qtd_txt) <= 0:
            flash("Selecione um produto e informe uma quantidade maior que zero.", "danger")
            return redirect(url_for(tipo))

        produto_id = int(produto_id)
        quantidade = int(qtd_txt)

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                produto = buscar_produto(cursor, produto_id)
                if produto is None:
                    flash("Produto não encontrado.", "danger")
                    return redirect(url_for(tipo))

                if tipo == "entrada":
                    cursor.execute(
                        "UPDATE produtos SET quantidade = quantidade + %s WHERE id = %s",
                        (quantidade, produto_id),
                    )
                else:
                    # só desconta se houver quantidade suficiente, evitando quantidade negativa
                    cursor.execute(
                        "UPDATE produtos SET quantidade = quantidade - %s "
                        "WHERE id = %s AND quantidade >= %s",
                        (quantidade, produto_id, quantidade),
                    )
                    if cursor.rowcount == 0:
                        conn.rollback()
                        flash(
                            f"Estoque insuficiente. {produto['nome']} tem apenas {produto["quantidade"]} unidades.",
                            "danger"
                        )
                        return redirect(url_for("saida", produto_id=produto_id))
                cursor.execute(
                    "INSERT INTO movimentacoes (produto_id, usuario_id, tipo, quantidade) " 
                    "VALUES (%s, %s, %s, %s)",
                    (produto_id, current_user.id, tipo, quantidade),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            flash("Erro ao registrar a movimentação. Nada foi alterado.", "danger")
            return redirect(url_for(tipo))
        finally:
            conn.close()

        verbo = "Entrada" if tipo == "entrada" else "Saída"
        flash(f"{verbo} de {quantidade} un de {produto['nome']} registrada.", "success")

        if tipo == "saida":
            saldo = produto["quantidade"] - quantidade
            minimo = produto["estoque_minimo"]
            if minimo > 0 and saldo <= minimo:
                flash(
                    f"Atenção: {produto['nome']} ficou com {saldo} un. "
                    f"(mínimo: {minimo}). Hora de repor!",
                    "warning",
                )
        return redirect(url_for("inicio"))


    # Buscar/escolher produto
    q = request.args.get("q", "").strip()
    produto_id = request.args.get("produto_id", "")
    produto = None
    produtos = []

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            if produto_id.isdigit():
                produto = buscar_produto(cursor, int(produto_id))
            elif q:
                cursor.execute(
                    "SELECT id, nome, codigo_barras, preco, quantidade, estoque_minimo " 
                    "FROM produtos "
                    "WHERE nome LIKE %s OR codigo_barras = %s OR id = %s "
                    "ORDER BY nome LIMIT 20",
                    (f"%{q}%", q, int(q) if q.isdigit() else -1),
                )
                produtos = cursor.fetchall()
                if len(produtos) == 1:
                    produto = produtos[0]
    finally:
        conn.close()

    return render_template(
        "movimentacao.html",
        tipo=tipo, q=q, produto=produto, produtos=produtos
    )


@app.route("/entrada", methods=["GET", "POST"])
@login_required
def entrada():
    return registrar_movimentacao("entrada")


@app.route("/saida", methods=["GET", "POST"])
@login_required
def saida():
    return registrar_movimentacao("saida")

# Historico de movimentacoes

def data_valida(texto):
    try:
        datetime.strptime(texto, "%Y-%m-%d")
        return texto
    except ValueError:
        return ""


@app.route("/historico")
@login_required
def historico():
    tipo = request.args.get("tipo", "")
    q = request.args.get("q", "").strip()
    data_ini = data_valida(request.args.get("de", ""))
    data_fim = data_valida(request.args.get("ate", ""))

    condicoes, params = [], []
    if tipo in ("entrada", "saida"):
        condicoes.append("m.tipo = %s")
        params.append(tipo)
    if q:
        condicoes.append("(p.nome LIKE %s OR p.codigo_barras = %s OR p.id = %s)")
        params += [f"%{q}%", q, int(q) if q.isdigit() else -1]
    if data_ini:
        condicoes.append("DATE(m.criado_em) >= %s")
        params.append(data_ini)
    if data_fim:
        condicoes.append("DATE(m.criado_em) <= %s")
        params.append(data_fim)

    sql = (
        "SELECT m.id, m.tipo, m.quantidade, m.criado_em, p.nome AS produto, u.nome AS usuario " \
        "FROM movimentacoes m " \
        "JOIN produtos p ON p.id = m.produto_id " \
        "JOIN usuarios u ON u.id = m.usuario_id"
    )
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)
    sql += " ORDER BY m.criado_em DESC, m.id DESC LIMIT 100"

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            movs = cursor.fetchall()
    finally:
        conn.close()

    return render_template(
        "historico.html", movs=movs, tipo=tipo, q=q, de=data_ini, ate=data_fim
    )



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)