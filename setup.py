from setuptools import setup, find_packages

setup(
    name="agente_SDR",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Adicione suas dependências aqui
        # Por exemplo:
        # "requests",
        # "fastapi",
        # "redis",
    ],
    python_requires=">=3.8",
    author="Seu Nome",
    description="Agente SDR",
)