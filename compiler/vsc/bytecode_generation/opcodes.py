from enum import IntEnum, auto


class OperandType(IntEnum):
    """
    Defines the type of an operand, encoded in the top 5 bits of a 32-bit integer.
    """

    # Register Types (Read/Write Memory)
    SCALAR_REG = 0
    VECTOR_REG = 1
    BOOLEAN_REG = 2
    STRING_REG = 3

    # Constant Pool Types (Read-Only Memory)
    SCALAR_CONST = 16
    VECTOR_CONST = 17
    BOOLEAN_CONST = 18
    STRING_CONST = 19


class OpCode(IntEnum):
    """
    Defines the complete Instruction Set Architecture (ISA) for the VSE.
    The name of each member defines the contract for the instruction's operands.
    Convention: FunctionName_<DEST-TYPES>_<SOURCE-TYPES>
    S=Scalar, V=Vector, B=Boolean, STR=String
    """

    # === Machine Control ===
    # Contract: No operands.
    HALT = 0

    # === Control Flow ===
    # Contract: srcs[0] is an IMMEDIATE integer jump target.
    JUMP = auto()
    # Contract: srcs[0] is a PACKED BOOLEAN_REG. srcs[1] is an IMMEDIATE integer jump target.
    JUMP_IF_FALSE = auto()

    # === Data Movement ===
    # Contract: All operands are PACKED. dests[0] receives a copy of srcs[0].
    copy_S_S = auto()
    copy_V_V = auto()
    copy_B_B = auto()
    copy_STR_STR = auto()

    # === Core Arithmetic ===
    # Contract: All operands are PACKED. Result is always a single destination.
    add_S_SS = auto()
    subtract_S_SS = auto()
    multiply_S_SS = auto()
    divide_S_SS = auto()
    power_S_SS = auto()
    add_V_VV = auto()
    subtract_V_VV = auto()
    multiply_V_VV = auto()
    divide_V_VV = auto()
    power_V_VV = auto()
    add_V_VS = auto()
    add_V_SV = auto()
    subtract_V_VS = auto()
    subtract_V_SV = auto()
    multiply_V_VS = auto()
    multiply_V_SV = auto()
    divide_V_VS = auto()
    divide_V_SV = auto()
    power_V_VS = auto()
    power_V_SV = auto()

    # === Core Math & Logic ===
    # Contract: All operands are PACKED.
    log_S_S = auto()
    exp_S_S = auto()
    not_B_B = auto()
    and_B_BB = auto()
    or_B_BB = auto()

    # === Core Comparison ===
    # Contract: All sources are PACKED. Result is always a single BOOLEAN_REG.
    gt_B_SS = auto()
    lt_B_SS = auto()
    gte_B_SS = auto()
    lte_B_SS = auto()
    eq_B_SS = auto()
    neq_B_SS = auto()
    eq_B_BB = auto()
    neq_B_BB = auto()
    eq_B_STRSTR = auto()
    neq_B_STRSTR = auto()

    # === Financial Functions ===
    # Contract: All operands are PACKED.
    BlackScholes_S_SSSSSSTR = auto()
    CapitalizeExpenses_SS_SVS = auto()
    Npv_S_SV = auto()

    # === Epidemiology Functions ===
    # Contract: All operands are PACKED.
    SirModel_VVV_SSSSSSS = auto()

    # === Series/Vector Functions ===
    # Contract: All operands are PACKED.
    SumVector_S_V = auto()
    GetElement_S_VS = auto()
    GrowSerie_V_SSS = auto()
    InterpolateSerie_V_SSS = auto()

    # === Statistical Samplers ===
    # Contract: All operands are PACKED.
    Normal_S_SS = auto()
    Lognormal_S_SS = auto()
    Beta_S_SS = auto()
    Uniform_S_SS = auto()
    Pert_S_SSS = auto()
    Triangular_S_SSS = auto()
    Bernoulli_S_S = auto()
