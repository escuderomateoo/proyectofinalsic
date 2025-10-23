def validar_luhn (numero_tarjeta: str) -> bool:
    """
    Comprueba si un numero de tarjeta de credito/debito es potencialmente valido utilizando el Algoritmo de Luhn
    """

    try:
        #limpiar el numero de tarjeta de espacios y/o guiones
        numero_tarjeta = numero_tarjeta.replace(" ", "").replace("-", "")
        if not (11 <= len(numero_tarjeta) <= 19): #longitud valida segun estandares internacionales
            return False  #falla si es demasiado corto o demasiado largo
        #convertir a digitos y revertir (Luhn se lee de derecha a izquierda)
        digitos = [int(d) for d in numero_tarjeta if d.isdigit()]
        
        digitos.reverse()

        #aplicar el algoritmo de Luhn
        suma = 0
        for i, digito in enumerate(digitos):
            if i % 2 == 1:   #duplicar digitos en posiciones impares (originalmente pares)
                digito_duplicado = digito * 2

                #si el resultado es > 9 , restar 9 o sumar sus digitos
                if digito_duplicado > 9:
                    digito_duplicado -= 9     

                suma += digito_duplicado

            else: #digitos en posiciones pares (originalmente impares), se suman directamente
                suma += digito         

        #el numero es valudo si la suma total es multiplo de 10
        return suma % 10 == 0
    
    #devuelve falso en caso de que el input no es un numero valido o este vacio
    except Exception as e:
        return False



    