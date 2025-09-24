from enum import IntEnum, auto


class OperandType(IntEnum):
    """
    Defines the type of an operand, encoded in the top 5 bits of a 32-bit integer.
    All values are 1-based to ensure a non-zero type header.
    """

    # Register Types (Read/Write Memory)
    SCALAR_REG = 1
    VECTOR_REG = 2
    BOOLEAN_REG = 3
    STRING_REG = 4

    # Constant Pool Types (Read-Only Memory)
    SCALAR_CONST = 17
    VECTOR_CONST = 18
    BOOLEAN_CONST = 19
    STRING_CONST = 20


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
    JUMP = 1
    # Contract: srcs[0] is a PACKED BOOLEAN_REG. srcs[1] is an IMMEDIATE integer jump target.
    JUMP_IF_FALSE = 2

    # === Data Movement ===
    # Contract: All operands are PACKED. dests[0] receives a copy of srcs[0].
    copy_S_S = 3
    copy_V_V = 4
    copy_B_B = 5
    copy_STR_STR = 6

    # === Core Arithmetic ===
    # Contract: All operands are PACKED. Result is always a single destination.
    add_S_SS = 7
    subtract_S_SS = 8
    multiply_S_SS = 9
    divide_S_SS = 10
    power_S_SS = 11
    add_V_VV = 12
    subtract_V_VV = 13
    multiply_V_VV = 14
    divide_V_VV = 15
    power_V_VV = 16
    add_V_VS = 17
    add_V_SV = 18
    subtract_V_VS = 19
    subtract_V_SV = 20
    multiply_V_VS = 21
    multiply_V_SV = 22
    divide_V_VS = 23
    divide_V_SV = 24
    power_V_VS = 25
    power_V_SV = 26

    # === Core Math & Logic ===
    # Contract: All operands are PACKED.
    log_S_S = 27
    exp_S_S = 28
    not_B_B = 29
    and_B_BB = 30
    or_B_BB = 31

    # === Core Comparison ===
    # Contract: All sources are PACKED. Result is always a single BOOLEAN_REG.
    gt_B_SS = 32
    lt_B_SS = 33
    gte_B_SS = 34
    lte_B_SS = 35
    eq_B_SS = 36
    neq_B_SS = 37
    eq_B_BB = 38
    neq_B_BB = 39
    eq_B_STRSTR = 40
    neq_B_STRSTR = 41

    # === Financial Functions ===
    # Contract: All operands are PACKED.
    BlackScholes_S_SSSSSSTR = 42
    CapitalizeExpenses_SS_SVS = 43
    Npv_S_SV = 44

    # === Epidemiology Functions ===
    # Contract: All operands are PACKED.
    SirModel_VVV_SSSSSSS = 45

    # === Series/Vector Functions ===
    # Contract: All operands are PACKED.
    SumVector_S_V = 46
    GetElement_S_VS = 47
    GrowSerie_V_SSS = 48
    InterpolateSerie_V_SSS = 49
    CompoundSerie_V_SV = 50
    VectorDelta_V_V = 51
    DeleteElement_V_VS = 52

    # === Statistical Samplers ===
    # Contract: All operands are PACKED.
    Normal_S_SS = 53
    Lognormal_S_SS = 54
    Beta_S_SS = 55
    Uniform_S_SS = 56
    Pert_S_SSS = 57
    Triangular_S_SSS = 58
    Bernoulli_S_S = 59
