#pragma once

// Centralized, strongly-typed error codes for the entire simulation engine.
enum class EngineErrc
{
    // General Errors
    UnknownError,
    UnknownFunction,
    MismatchedArgumentType,
    IndexOutOfBounds,
    OutputFileWriteFailed,

    // Mathematical Errors
    DivisionByZero,
    LogOfNonPositive,
    InvalidPowerOperation,

    // Vector/Series Errors
    VectorSizeMismatch,
    EmptyVectorOperation,

    // Conditional/Logical Errors
    ConditionNotBoolean,
    LogicalOperatorRequiresBoolean,

    // Sampler Errors
    InvalidSamplerParameters,

    // I/O Errors
    CsvFileNotFound,
    CsvColumnNotFound,
    CsvRowIndexOutOfBounds,
    CsvConversionError,
    RecipeFileNotFound,
    RecipeParseError,
    RecipeConfigError,

    // Arity (Argument Count) Errors
    IncorrectArgumentCount
};