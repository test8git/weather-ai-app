from langchain_core.tools import tool
from sympy import sympify
from sympy import sqrt
from sympy import sin
from sympy import cos
from sympy import tan
from sympy import log
from sympy import factorial
from sympy import pi

import re


@tool(description=
    """
    Perform mathematical calculations.
    """)
def calculate_expression(expression: str):    
    try:
        print("Calculator called")
        
        exp = expression.lower().strip()
        exp = exp.replace("^", "**")
        exp = re.sub(r'(\d+)\s*%', r'(\1/100)', exp)
        exp = exp.replace("pi", str(pi))

        result = sympify(exp)

        # Convert to int if it's a whole number
        if result.is_number:
            value = float(result)

            if value.is_integer():
                result = int(value)
            else:
                result = round(value, 10)

        return f"{expression} = {result}"

    except Exception as e:
        return f"Calculation Error: {e}"