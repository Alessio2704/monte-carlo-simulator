#pragma once

#include "include/engine/core/datastructures.h"
#include <string>
#include <vector>

// Writes the results of a simulation to a CSV file.
// This function handles both scalar and vector trial values, creating an appropriate
// header and data structure for each.
void write_results_to_csv(const std::string &path, const std::vector<TrialValue> &results);