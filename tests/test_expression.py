import pytest
from bist_terminal.strategies.expression import compile_expression,UnsafeExpression

def test_safe_formula(): assert compile_expression('pe < sector_pe_median * 0.8 and roe > 0.2')({'pe':6,'sector_pe_median':10,'roe':0.25})
def test_no_function_calls():
    with pytest.raises(UnsafeExpression): compile_expression('__import__("os").system("id")')
