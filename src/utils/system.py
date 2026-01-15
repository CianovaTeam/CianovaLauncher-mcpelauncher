import subprocess

def is_nvidia_gpu_present():
    """
    Verifica si hay una GPU de Nvidia presente en el sistema ejecutando 'lspci'.
    """
    try:
        # Usamos subprocess.run para ejecutar el pipeline. check=True asegura que si grep
        # no encuentra nada (y devuelve un código de error > 0), se lance una excepción.
        subprocess.run(
            "lspci | grep -i nvidia",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Si el comando se ejecuta con éxito, significa que grep encontró una coincidencia.
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        # CalledProcessError: Ocurre si grep no encuentra ninguna línea (código de salida 1).
        # FileNotFoundError: Ocurre si lspci no está disponible en el sistema.
        return False
