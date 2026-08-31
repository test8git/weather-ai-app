import json
import math
import operator
from typing import Any
from common.request_context import (current_selected_ai_modal)
from services.llm_factory import get_llm

from langchain_core.prompts import ChatPromptTemplate


# ============================================================
# AI CALCULATION PLANNER
# ============================================================

CALCULATION_SYSTEM_PROMPT = """
You are a spreadsheet calculation planner.

Your job is to understand a user's calculation request
and convert it into a SAFE JSON calculation plan.

You are given:
1. The user's calculation request.
2. The columns available in a Google Sheet.
3. The spreadsheet rows.

IMPORTANT:
- Do NOT write Python.
- Do NOT write arbitrary code.
- Do NOT invent column names.
- Use only columns that actually exist.
- Return ONLY valid JSON.
- Build calculations using the supported operations below.

Supported operations:

VALUE
    Get a value from a column.

SUM
    Sum numeric values in a column.

AVERAGE
    Calculate arithmetic average.

MIN
    Minimum numeric value.

MAX
    Maximum numeric value.

COUNT
    Count numeric/non-empty values.

COUNT_ROWS
    Count rows.

MEDIAN
    Calculate median.

ADD
    Add two calculation expressions.

SUBTRACT
    Subtract the second expression from the first.

MULTIPLY
    Multiply two calculation expressions.

DIVIDE
    Divide the first expression by the second.

PERCENTAGE
    Calculate:
        (value / total) * 100

ABS
    Absolute value.

ROUND
    Round a numeric result.

FILTER
    Filter rows before calculating.

For FILTER use:

{
    "operation": "filter",
    "column": "Status",
    "operator": "equals",
    "value": "Completed",
    "then": {
        ...
    }
}

Allowed filter operators:

equals
not_equals
greater_than
greater_than_or_equal
less_than
less_than_or_equal
contains
not_contains

Calculation expressions are recursive.

Example user request:

"Calculate total revenue minus total refunds"

Return:

{
    "operation": "subtract",
    "left": {
        "operation": "sum",
        "column": "Revenue"
    },
    "right": {
        "operation": "sum",
        "column": "Refund"
    }
}

Example:

"Calculate average revenue for completed orders"

Return:

{
    "operation": "filter",
    "column": "Status",
    "operator": "equals",
    "value": "Completed",
    "then": {
        "operation": "average",
        "column": "Revenue"
    }
}

Example:

"What percentage of revenue was refunded?"

Return:

{
    "operation": "percentage",
    "value": {
        "operation": "sum",
        "column": "Refund"
    },
    "total": {
        "operation": "sum",
        "column": "Revenue"
    }
}

Return ONLY JSON.
"""


# ============================================================
# CREATE MODEL
# ============================================================

def get_calculation_llm():
    """
    Create the LLM used specifically for spreadsheet
    calculation planning.

    Keep this separate from the main agent model so that
    calculation behaviour can evolve independently.
    """

    selected_modal = current_selected_ai_modal.get()

    return get_llm(selected_modal)


# ============================================================
# AI PLANNER
# ============================================================

async def generate_calculation_plan(calculation_request: str, rows: list[dict[str, Any]],) -> dict[str, Any]:

    if not rows:
        raise ValueError("The spreadsheet contains no data rows.")

    columns = list(rows[0].keys())

    # Do not unnecessarily send huge datasets to the planner.
    # The planner mainly needs schema + representative data.
    sample_rows = rows[:20]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CALCULATION_SYSTEM_PROMPT),
            (
                "human",
                """
                User calculation request:

                {calculation_request}

                Available spreadsheet columns:

                {columns}

                Sample spreadsheet rows:

                {sample_rows}

                Create the safest calculation plan for the user's request.
                """,
            ),
        ]
    )

    chain = prompt | get_calculation_llm()

    response = await chain.ainvoke(
        {
            "calculation_request": calculation_request,
            "columns": json.dumps(columns),
            "sample_rows": json.dumps(
                sample_rows,
                default=str,
                ensure_ascii=False,
            ),
        }
    )

    content = response.content

    if isinstance(content, list):
        content = "".join(
            block.get("text", "")
            if isinstance(block, dict)
            else str(block)
            for block in content
        )

    content = str(content).strip()

    # Handle accidental markdown fences.
    if content.startswith("```"):
        content = content.replace("```json", "")
        content = content.replace("```", "")
        content = content.strip()

    try:
        plan = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"AI returned invalid calculation plan: {content}"
        ) from exc

    if not isinstance(plan, dict):
        raise ValueError("AI calculation plan must be a JSON object.")

    return plan


# ============================================================
# VALUE CONVERSION
# ============================================================

def to_number(value: Any) -> float | None:

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return None

        return float(value)

    text = str(value).strip()

    if not text:
        return None

    # Remove common formatting.
    text = text.replace(",", "")
    text = text.replace("$", "")
    text = text.replace("₹", "")
    text = text.replace("€", "")
    text = text.replace("£", "")

    # Handle percentage strings.
    if text.endswith("%"):
        try:
            return float(text[:-1]) / 100
        except ValueError:
            return None

    try:
        return float(text)
    except ValueError:
        return None


def get_numeric_values(rows: list[dict[str, Any]], column: str,) -> list[float]:

    values = []

    for row in rows:

        if column not in row:
            continue

        number = to_number(row.get(column))

        if number is not None:
            values.append(number)

    return values


# ============================================================
# FILTER ENGINE
# ============================================================

def compare_value(actual: Any, operator_name: str, expected: Any,) -> bool:

    actual_number = to_number(actual)
    expected_number = to_number(expected)

    if (
        actual_number is not None
        and expected_number is not None
    ):
        left = actual_number
        right = expected_number

    else:
        left = str(actual or "").strip().casefold()
        right = str(expected or "").strip().casefold()

    if operator_name == "equals":
        return left == right

    if operator_name == "not_equals":
        return left != right

    if operator_name == "greater_than":
        return left > right

    if operator_name == "greater_than_or_equal":
        return left >= right

    if operator_name == "less_than":
        return left < right

    if operator_name == "less_than_or_equal":
        return left <= right

    if operator_name == "contains":
        return str(right) in str(left)

    if operator_name == "not_contains":
        return str(right) not in str(left)

    raise ValueError(
        f"Unsupported filter operator: {operator_name}"
    )


def filter_rows(rows: list[dict[str, Any]], column: str, operator_name: str, value: Any,) -> list[dict[str, Any]]:

    return [
        row
        for row in rows
        if compare_value(
            row.get(column),
            operator_name,
            value,
        )
    ]


# ============================================================
# SAFE CALCULATION EXECUTOR
# ============================================================

def execute_calculation(plan: dict[str, Any], rows: list[dict[str, Any]],) -> Any:

    if not isinstance(plan, dict):
        raise ValueError("Calculation plan must be an object.")

    operation = str(
        plan.get("operation", "")
    ).strip().lower()

    # --------------------------------------------------------
    # Aggregations
    # --------------------------------------------------------

    if operation in {
        "sum",
        "total",
    }:

        column = plan.get("column")

        if not column:
            raise ValueError("SUM requires a column.")

        values = get_numeric_values(rows, column)

        return sum(values)

    if operation in {
        "average",
        "avg",
        "mean",
    }:

        column = plan.get("column")

        if not column:
            raise ValueError("AVERAGE requires a column.")

        values = get_numeric_values(rows, column)

        if not values:
            return None

        return sum(values) / len(values)

    if operation in {
        "min",
        "minimum",
    }:

        column = plan.get("column")

        if not column:
            raise ValueError("MIN requires a column.")

        values = get_numeric_values(rows, column)

        return min(values) if values else None

    if operation in {
        "max",
        "maximum",
    }:

        column = plan.get("column")

        if not column:
            raise ValueError("MAX requires a column.")

        values = get_numeric_values(rows, column)

        return max(values) if values else None

    if operation == "median":

        column = plan.get("column")

        if not column:
            raise ValueError("MEDIAN requires a column.")

        values = get_numeric_values(rows, column)

        if not values:
            return None

        values = sorted(values)

        middle = len(values) // 2

        if len(values) % 2:
            return values[middle]

        return (
            values[middle - 1]
            + values[middle]
        ) / 2

    if operation in {
        "count",
        "count_non_empty",
    }:

        column = plan.get("column")

        if not column:
            return len(rows)

        return sum(
            1
            for row in rows
            if row.get(column) is not None
            and str(row.get(column)).strip() != ""
        )

    if operation == "count_rows":
        return len(rows)

    # --------------------------------------------------------
    # Arithmetic
    # --------------------------------------------------------

    if operation in {
        "add",
        "sum_values",
    }:

        left = execute_calculation(
            plan["left"],
            rows,
        )

        right = execute_calculation(
            plan["right"],
            rows,
        )

        return left + right

    if operation in {
        "subtract",
        "minus",
    }:

        left = execute_calculation(
            plan["left"],
            rows,
        )

        right = execute_calculation(
            plan["right"],
            rows,
        )

        return left - right

    if operation in {
        "multiply",
        "multiply_values",
    }:

        left = execute_calculation(
            plan["left"],
            rows,
        )

        right = execute_calculation(
            plan["right"],
            rows,
        )

        return left * right

    if operation in {
        "divide",
        "divide_values",
    }:

        left = execute_calculation(
            plan["left"],
            rows,
        )

        right = execute_calculation(
            plan["right"],
            rows,
        )

        if right == 0:
            raise ValueError(
                "Cannot divide by zero."
            )

        return left / right

    # --------------------------------------------------------
    # Percentage
    # --------------------------------------------------------

    if operation == "percentage":

        value = execute_calculation(
            plan["value"],
            rows,
        )

        total = execute_calculation(
            plan["total"],
            rows,
        )

        if total == 0:
            raise ValueError(
                "Cannot calculate percentage using zero total."
            )

        return (value / total) * 100

    # --------------------------------------------------------
    # Absolute value
    # --------------------------------------------------------

    if operation == "abs":

        value = execute_calculation(
            plan["value"],
            rows,
        )

        return abs(value)

    # --------------------------------------------------------
    # Round
    # --------------------------------------------------------

    if operation == "round":

        value = execute_calculation(
            plan["value"],
            rows,
        )

        digits = int(
            plan.get("digits", 2)
        )

        return round(value, digits)

    # --------------------------------------------------------
    # Filter
    # --------------------------------------------------------

    if operation == "filter":

        filtered_rows = filter_rows(
            rows=rows,
            column=plan["column"],
            operator_name=plan["operator"],
            value=plan.get("value"),
        )

        then_plan = plan.get("then")

        if not then_plan:
            return filtered_rows

        return execute_calculation(
            then_plan,
            filtered_rows,
        )

    # --------------------------------------------------------
    # Constant value
    # --------------------------------------------------------

    if operation == "value":

        return plan.get("value")

    raise ValueError(
        f"Unsupported calculation operation: {operation}"
    )


# ============================================================
# MAIN AI CALCULATION FUNCTION
# ============================================================

async def calculate_with_ai(rows: list[dict[str, Any]], calculation_request: str,) -> dict[str, Any]:

    if not calculation_request:
        raise ValueError(
            "Calculation request is required."
        )

    if not rows:
        return {
            "result": None,
            "plan": None,
            "row_count": 0,
            "message": "The spreadsheet contains no data."
        }

    # --------------------------------------------------------
    # 1. Ask AI to understand the calculation.
    # --------------------------------------------------------

    plan = await generate_calculation_plan(
        calculation_request=calculation_request,
        rows=rows,
    )

    # --------------------------------------------------------
    # 2. Execute only the structured/safe plan.
    # --------------------------------------------------------

    result = execute_calculation(
        plan=plan,
        rows=rows,
    )

    return {
        "result": result,
        "plan": plan,
        "row_count": len(rows),
    }