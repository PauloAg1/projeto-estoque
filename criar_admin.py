import getpass

from werkzeug.security import generate_password_hash

from db import get_connection

def criar_admin():
    print("===Criação do ADMIN")
    nome = input("Nome completo: ")
    usuario = input("Nome de usuário para login: ")
    senha = getpass.getpass("Senha: ")
    confirmacao = getpass.getpass("Confirme a senha: ")

    if senha != confirmacao:
        print("As senhas não conferem. Admin NÃO FOI CRIADO.")
        return

    senha_hash = generate_password_hash(senha)

    conn = get_connection()

    try:    
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO usuarios (nome, usuario, senha_hash, perfil) "
                "VALUES (%s, %s, %s, 'admin')",
                (nome, usuario, senha_hash)
            )
        conn.commit() # confirma a gravacao
        print(f"Usuário administrador '{usuario}' criado com sucesso.")
    finally:
        conn.close()

if __name__ == "__main__":
    criar_admin()