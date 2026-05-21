from __future__ import annotations

import ast
import operator
from typing import Any, Dict

from .exceptions import ConditionEvaluationError


class SafeConditionEvaluator:
    """Безопасный вычислитель простых логических условий.

    Поддерживаемые примеры условий:
        amount < 5000
        context.amount <= 10000
        role == 'manager'
        amount > 1000 and role in ['manager', 'admin']
    """

    _binary_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
    }

    _compare_ops = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
    }

    def __init__(self, context: Dict[str, Any]):
        self.context = context

    def evaluate(self, expression: str) -> bool:
        try:
            tree = ast.parse(expression, mode="eval")
            result = self._eval_node(tree.body)
            return bool(result)
        except ConditionEvaluationError:
            raise
        except Exception as exc:
            raise ConditionEvaluationError(f"Не удалось вычислить условие: {expression}", details={"condition": expression, "error": str(exc)}, hint="Проверьте, что все переменные условия переданы в context.") from exc

    def _eval_node(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            if node.id == "context":
                return self.context
            if node.id in self.context:
                return self.context[node.id]
            raise ConditionEvaluationError(f"Неизвестная переменная в условии: {node.id}", details={"variable": node.id, "available_variables": list(self.context.keys())}, hint="Передайте эту переменную через context или исправьте условие в YAML.")

        if isinstance(node, ast.Attribute):
            value = self._eval_node(node.value)
            if isinstance(value, dict):
                if node.attr in value:
                    return value[node.attr]
                raise ConditionEvaluationError(f"Неизвестный атрибут context: {node.attr}", details={"attribute": node.attr, "available_variables": list(value.keys())})
            return getattr(value, node.attr)

        if isinstance(node, ast.Subscript):
            value = self._eval_node(node.value)
            key = self._eval_node(node.slice)
            return value[key]

        if isinstance(node, ast.List):
            return [self._eval_node(item) for item in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(item) for item in node.elts)

        if isinstance(node, ast.Dict):
            return {self._eval_node(k): self._eval_node(v) for k, v in zip(node.keys, node.values)}

        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self._eval_node(value) for value in node.values)
            if isinstance(node.op, ast.Or):
                return any(self._eval_node(value) for value in node.values)

        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return not self._eval_node(node.operand)
            if isinstance(node.op, ast.USub):
                return -self._eval_node(node.operand)

        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self._binary_ops:
                raise ConditionEvaluationError(f"Неподдерживаемый арифметический оператор: {op_type.__name__}", details={"operator": op_type.__name__})
            return self._binary_ops[op_type](self._eval_node(node.left), self._eval_node(node.right))

        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                op_type = type(op)
                if op_type not in self._compare_ops:
                    raise ConditionEvaluationError(f"Неподдерживаемый оператор сравнения: {op_type.__name__}", details={"operator": op_type.__name__})
                right = self._eval_node(comparator)
                if not self._compare_ops[op_type](left, right):
                    return False
                left = right
            return True

        raise ConditionEvaluationError(f"Неподдерживаемый элемент выражения: {type(node).__name__}", details={"element": type(node).__name__}, hint="В условиях поддерживаются простые сравнения, and/or/not, in/not in и арифметические операции.")
