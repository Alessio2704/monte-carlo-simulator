#pragma once

#include "include/engine/core/DataStructures.h"
#include <string>
#include <vector>

void write_results_to_csv(const std::string &path, const std::vector<TrialValue> &results);