from fractions import Fraction
from itertools import permutations

from plan.snapshot import FrozenPlan

# 微量放行列:先在严格正比例下取长期时间平均(含周期链的 Cesàro 平均),
# 再令比例趋近于零取右极限。正比例下固定计划各工位互达,平稳分布唯一,
# 由马尔可夫链树定理给出:工位 i 的平稳概率正比于以 i 为根的支撑树形图
# 权重之和,而每条路线概率是比例 x 的单项式,故该权重和是 x 的精确多项式
# W_i(x)。π_i(x) = W_i(x) / Σ_j W_j(x) 的右极限只取决于各 W_i 的最低次项:
# 记 d_i 为 W_i 的最低次数,d = min d_i,则极限在 d_i = d 的工位上按最低次
# 系数比例分配,其余工位为零。全部系数为 Fraction,结果精确。

Polynomial = tuple  # tuple[Fraction, ...],下标即次数,去尾零;空元组为零多项式


def _as_polynomial(coefficients) -> Polynomial:
    result = list(coefficients)
    while result and not result[-1]:
        result.pop()
    return tuple(result)


def _add(left: Polynomial, right: Polynomial) -> Polynomial:
    size = max(len(left), len(right))
    return _as_polynomial([
        (left[degree] if degree < len(left) else Fraction(0))
        + (right[degree] if degree < len(right) else Fraction(0))
        for degree in range(size)
    ])


def _negate(polynomial: Polynomial) -> Polynomial:
    return tuple(-coefficient for coefficient in polynomial)


def _multiply(left: Polynomial, right: Polynomial) -> Polynomial:
    if not left or not right:
        return ()
    result = [Fraction(0)] * (len(left) + len(right) - 1)
    for first, first_coefficient in enumerate(left):
        if not first_coefficient:
            continue
        for second, second_coefficient in enumerate(right):
            if second_coefficient:
                result[first + second] += first_coefficient * second_coefficient
    return _as_polynomial(result)


def _symbolic_laplacian(plan: FrozenPlan) -> tuple[tuple[Polynomial, ...], ...]:
    """L(x) = I - P(x) 的多项式表示;同端点路线相加,本站路线与留驻相互抵消。"""
    index = {station: position for position, station in enumerate(plan.stations)}
    size = len(index)
    laplacian = [[() for _ in range(size)] for _ in range(size)]
    for route in plan.routes:
        term = _as_polynomial([Fraction(0)] * route.releases + [route.base_probability])
        source = index[route.source]
        destination = index[route.destination]
        if source == destination:
            continue
        laplacian[source][source] = _add(laplacian[source][source], term)
        laplacian[source][destination] = _add(laplacian[source][destination], _negate(term))
    return tuple(tuple(row) for row in laplacian)


def _odd_permutation(perm: tuple[int, ...]) -> bool:
    inversions = 0
    for first in range(len(perm)):
        for second in range(first + 1, len(perm)):
            if perm[first] > perm[second]:
                inversions += 1
    return bool(inversions % 2)


def _determinant(matrix: tuple[tuple[Polynomial, ...], ...]) -> Polynomial:
    size = len(matrix)
    if size == 0:
        return (Fraction(1),)
    total: Polynomial = ()
    for perm in permutations(range(size)):
        product: Polynomial = (Fraction(1),)
        for row, column in enumerate(perm):
            product = _multiply(product, matrix[row][column])
        total = _add(total, _negate(product) if _odd_permutation(perm) else product)
    return total


def _root_weight(laplacian: tuple[tuple[Polynomial, ...], ...], root: int) -> Polynomial:
    size = len(laplacian)
    minor = tuple(
        tuple(laplacian[row][column] for column in range(size) if column != root)
        for row in range(size)
        if row != root
    )
    return _determinant(minor)


def rare_occupation_limit(plan: FrozenPlan) -> tuple[Fraction, ...]:
    """正比例长期时间平均在比例趋近于零时的精确右极限,按原工位顺序返回。"""
    laplacian = _symbolic_laplacian(plan)
    leading = []
    for root in range(len(plan.stations)):
        polynomial = _root_weight(laplacian, root)
        if not polynomial:
            raise ValueError('fixed plan stations must be mutually reachable at positive release ratios')
        degree = next(degree for degree, coefficient in enumerate(polynomial) if coefficient)
        leading.append((degree, polynomial[degree]))
    lowest = min(degree for degree, _ in leading)
    total = sum(coefficient for degree, coefficient in leading if degree == lowest)
    return tuple(
        coefficient / total if degree == lowest else Fraction(0)
        for degree, coefficient in leading
    )
