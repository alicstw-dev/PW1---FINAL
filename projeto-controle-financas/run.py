from app import create_app

# Chama a função que cria a nossa aplicação
app = create_app()

# Executa o servidor
if __name__ == '__main__':
    app.run(debug=True)