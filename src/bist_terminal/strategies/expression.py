from __future__ import annotations
import ast, operator

_ALLOWED_NODES=(ast.Expression,ast.BoolOp,ast.BinOp,ast.UnaryOp,ast.Compare,ast.Name,ast.Load,ast.Constant,ast.And,ast.Or,ast.Not,ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Mod,ast.Pow,ast.USub,ast.UAdd,ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE)
_BIN={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Mod:operator.mod,ast.Pow:operator.pow}
_CMP={ast.Eq:operator.eq,ast.NotEq:operator.ne,ast.Lt:operator.lt,ast.LtE:operator.le,ast.Gt:operator.gt,ast.GtE:operator.ge}

class UnsafeExpression(ValueError): pass

class _Evaluator:
    def __init__(self,row:dict): self.row=row
    def visit(self,node):
        if isinstance(node,ast.Expression): return self.visit(node.body)
        if isinstance(node,ast.Constant): return node.value
        if isinstance(node,ast.Name): return self.row.get(node.id)
        if isinstance(node,ast.BoolOp):
            vals=[bool(self.visit(v)) for v in node.values]
            return all(vals) if isinstance(node.op,ast.And) else any(vals)
        if isinstance(node,ast.UnaryOp):
            v=self.visit(node.operand)
            if isinstance(node.op,ast.Not): return not bool(v)
            if isinstance(node.op,ast.USub): return -v
            if isinstance(node.op,ast.UAdd): return +v
        if isinstance(node,ast.BinOp): return _BIN[type(node.op)](self.visit(node.left),self.visit(node.right))
        if isinstance(node,ast.Compare):
            left=self.visit(node.left)
            for op,right_node in zip(node.ops,node.comparators):
                right=self.visit(right_node)
                if not _CMP[type(op)](left,right): return False
                left=right
            return True
        raise UnsafeExpression(f'Unsupported node: {type(node).__name__}')

def compile_expression(expr:str):
    tree=ast.parse(expr,mode='eval')
    for node in ast.walk(tree):
        if not isinstance(node,_ALLOWED_NODES): raise UnsafeExpression(f'Forbidden expression node: {type(node).__name__}')
    names={n.id for n in ast.walk(tree) if isinstance(n,ast.Name)}
    def fn(row:dict):
        try: return bool(_Evaluator(row).visit(tree))
        except (TypeError,ZeroDivisionError,KeyError,ValueError): return False
    fn.required_fields=names
    return fn
