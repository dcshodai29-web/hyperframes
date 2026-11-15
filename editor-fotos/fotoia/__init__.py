"""fotoia — toolkit de edição fotográfica por IA, feito para ser operado por um agente.

Cada módulo expõe funções puras (array -> array) e a CLI (`python -m fotoia`)
expõe as mesmas operações como comandos arquivo -> arquivo.

Convenções:
- Imagens são `np.ndarray float32` HxWx3, sRGB, intervalo [0, 1].
- Máscaras e alfas são `np.ndarray float32` HxW em [0, 1] (1 = selecionado / opaco).
- Nenhuma função escreve sobre o arquivo de entrada.
"""

__version__ = "1.0.0"
