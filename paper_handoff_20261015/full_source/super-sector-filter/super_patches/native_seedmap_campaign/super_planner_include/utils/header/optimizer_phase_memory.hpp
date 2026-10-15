#pragma once

#include <cstdlib>
#include <fstream>
#include <string>

namespace super_utils {

struct ProcessResidentMemory {
    double rss_mib{-1.0};
    double swap_mib{-1.0};
};

inline bool optimizerPhaseMemoryTraceEnabled() {
    static const bool enabled = []() {
        const char *value =
                std::getenv("SUPER_OPTIMIZER_PHASE_MEMORY_TRACE");
        if (value == nullptr) {
            return false;
        }
        const std::string text(value);
        return text == "1" || text == "true" || text == "TRUE" ||
                text == "yes" || text == "on";
    }();
    return enabled;
}

inline ProcessResidentMemory readProcessResidentMemory() {
    ProcessResidentMemory result;
    std::ifstream status("/proc/self/status");
    std::string key;
    while (status >> key) {
        if (key == "VmRSS:" || key == "VmSwap:") {
            double value_kib = -1.0;
            std::string unit;
            status >> value_kib >> unit;
            const double value_mib = value_kib / 1024.0;
            if (key == "VmRSS:") {
                result.rss_mib = value_mib;
            } else {
                result.swap_mib = value_mib;
            }
        } else {
            std::string rest;
            std::getline(status, rest);
        }
    }
    return result;
}

}  // namespace super_utils
