import os
from functools import wraps

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
                (usuario_id)
            
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
    return render_template("inicio.html")


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

            novo_status = 0 if linha["ativo"] else 0
            cursor.execute(
                "UPDATE usuarios SET ativo = %s WHERE id = %s", (novo_status, usuario_id))

            conn.commit()
    finally:
        conn.close()

    acao = "reativado" if novo_status == 1 else "desativado"
    flash(f"Usuário {acao} com sucesso.", "success")
    return redirect(url_for("listar_usuarios"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)