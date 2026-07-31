"""
Módulo utilitario para conversión de montos numéricos a su representación en texto oficial en español.
Formato: "Son: Ciento Setenta y Tres pesos 12/100 M.N."
"""

UNIDADES = (
    "", "Un", "Dos", "Tres", "Cuatro", "Cinco", "Seis", "Siete", "Ocho", "Nueve",
    "Diez", "Once", "Doce", "Trece", "Catorce", "Quince", "Dieciséis", "Diecisiete",
    "Dieciocho", "Diecinueve", "Veinte", "Veintiuno", "Veintidós", "Veintitrés",
    "Veinticuatro", "Veinticinco", "Veintiséis", "Veintisiete", "Veintiocho", "Veintinueve"
)

DECENAS = (
    "", "", "", "Treinta", "Cuarenta", "Cincuenta", "Sesenta", "Setenta", "Ochenta", "Noventa"
)

CENTENAS = (
    "", "Ciento", "Doscientos", "Trescientos", "Cuatrocientos", "Quinientos",
    "Seiscientos", "Setecientos", "Ochocientos", "Novecientos"
)


def _seccion(numero, divisor, str_singular, str_plural):
    cientos = numero // divisor
    resto = numero % divisor
    letras = ""
    if cientos > 0:
        if cientos > 1:
            letras = _numero_a_letras(cientos) + " " + str_plural
        else:
            letras = str_singular

    if resto > 0:
        letras += " "

    return letras, resto


def _centenas(numero):
    if numero < 30:
        return UNIDADES[numero]
    elif numero < 100:
        decena = numero // 10
        resto = numero % 10
        if resto > 0:
            return DECENAS[decena] + " y " + UNIDADES[resto]
        return DECENAS[decena]
    else:
        centena = numero // 100
        resto = numero % 100
        if centena == 1 and resto == 0:
            return "Cien"
        return CENTENAS[centena] + (" " + _centenas(resto) if resto > 0 else "")


def _numero_a_letras(numero):
    if numero == 0:
        return "Cero"

    millones, resto = _seccion(numero, 1000000, "Un Millón", "Millones")
    miles, resto = _seccion(resto, 1000, "Un Mil", "Mil")
    cientos = _centenas(resto)

    resultado = millones + miles + cientos
    return resultado.strip()


def numero_a_letras_mxn(monto, moneda="MXN"):
    """
    Convierte un float (ej: 309.12) a texto oficial en español:
    "Son: Ciento Setenta y Tres pesos 12/100 M.N."
    """
    try:
        monto = float(monto)
    except (ValueError, TypeError):
        return "Son: Cero pesos 00/100 M.N."

    entero = int(monto)
    centavos = int(round((monto - entero) * 100))

    if centavos >= 100:
        entero += 1
        centavos = 0

    texto_entero = _numero_a_letras(entero)
    suffix = "M.N." if "USD" not in str(moneda).upper() else "U.S.D."
    moneda_label = "pesos" if "USD" not in str(moneda).upper() else "dólares"

    return f"Son: {texto_entero} {moneda_label} {centavos:02d}/100 {suffix}"
