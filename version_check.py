import subprocess

def main():
    try:
        flask_version = subprocess.check_output(['flask', '--version']).decode()
    except Exception as e:
        flask_version = f"Flask no encontrado: {e}"

    try:
        gunicorn_version = subprocess.check_output(['gunicorn', '--version']).decode()
    except Exception as e:
        gunicorn_version = f"Gunicorn no encontrado: {e}"

    print("Versiones instaladas:")
    print(flask_version)
    print(gunicorn_version)

if __name__ == "__main__":
    main()
