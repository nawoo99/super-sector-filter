#include <path_search/parent_chain.hpp>
#include <super_core/planner_sequence_guards.hpp>

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace chain = path_search::parent_chain;
namespace sequence = super_planner::sequence_guards;
namespace {
std::size_t checks = 0;
void require(const bool condition, const std::string& name) {
    ++checks;
    if (!condition) throw std::runtime_error(name);
}

struct Node {
    Node* father_ptr{nullptr};
    // Deliberately unrelated metadata: reconstruction must not add new
    // rounds/cost semantics, including for legacy frontier nodes.
    int rounds{0};
    double distance_score{std::numeric_limits<double>::quiet_NaN()};
};

bool referenceChain(Node* node, const std::size_t bound,
                    std::vector<Node*>& expected) {
    expected.clear();
    if (!node) return false;
    while (node) {
        if (expected.size() == bound) return false;
        for (auto* previous : expected) {
            if (previous == node) return false;
        }
        expected.push_back(node);
        node = node->father_ptr;
    }
    return true;
}

void parentChainTests() {
    Node singleton;
    std::vector<Node*> output{&singleton};
    require(chain::reconstruct(static_cast<Node*>(nullptr), 1, output) ==
                    chain::Result::NULL_START && output.empty(),
            "null root rejects and clears old output");
    require(chain::reconstruct(&singleton, 0, output) == chain::Result::NODE_LIMIT &&
                    output.empty(), "zero node budget rejects");
    require(chain::reconstruct(&singleton, 1, output) == chain::Result::SUCCESS &&
                    output == std::vector<Node*>{&singleton},
            "singleton succeeds at exact bound despite unrelated NaN metadata");

    Node child{&singleton, 99, -1.0};
    require(chain::reconstruct(&child, 2, output) == chain::Result::SUCCESS &&
                    output == std::vector<Node*>({&child, &singleton}),
            "valid parent order and mixed metadata unchanged");
    require(chain::reconstruct(&child, 1, output) == chain::Result::NODE_LIMIT &&
                    output.empty(), "overbound chain never returns partial output");

    singleton.father_ptr = &singleton;
    const auto old_capacity = output.capacity();
    require(chain::reconstruct(&singleton, 1000000, output) == chain::Result::CYCLE &&
                    output.empty() && output.capacity() == old_capacity,
            "self cycle rejected before allocating path storage");
    singleton.father_ptr = &child;
    require(chain::reconstruct(&child, 1000000, output) == chain::Result::CYCLE &&
                    output.empty(), "two node cycle rejects");

    // Exhaust all graphs with up to five live nodes (each parent is null or
    // another node), all starting nodes, and both full/one-short budgets.
    for (std::size_t count = 1; count <= 5; ++count) {
        std::vector<Node> nodes(count);
        std::size_t graphs = 1;
        for (std::size_t i = 0; i < count; ++i) graphs *= count + 1;
        for (std::size_t graph = 0; graph < graphs; ++graph) {
            auto code = graph;
            for (std::size_t i = 0; i < count; ++i) {
                const auto target = code % (count + 1);
                code /= count + 1;
                nodes[i].father_ptr = target == count ? nullptr : &nodes[target];
            }
            for (auto& node : nodes) {
                for (const auto bound : {count, count - 1}) {
                    std::vector<Node*> expected;
                    const bool valid = referenceChain(&node, bound, expected);
                    const auto result = chain::reconstruct(&node, bound, output);
                    require((result == chain::Result::SUCCESS) == valid,
                            "exhaustive graph acceptance matches bounded reference");
                    require(valid ? output == expected : output.empty(),
                            "exhaustive graph preserves full path or clears output");
                }
            }
        }
    }

    std::vector<Node> long_chain(100000);
    for (std::size_t i = 1; i < long_chain.size(); ++i) {
        long_chain[i].father_ptr = &long_chain[i - 1];
    }
    require(chain::reconstruct(&long_chain.back(), long_chain.size(), output) ==
                    chain::Result::SUCCESS && output.size() == long_chain.size(),
            "long finite chain has no arbitrary small cutoff");
    for (std::size_t i = 0; i < output.size(); ++i) {
        require(output[i] == &long_chain[long_chain.size() - 1 - i],
                "long chain order matches legacy reconstruction");
    }
    long_chain.front().father_ptr = &long_chain[173];
    require(chain::reconstruct(&long_chain.back(), long_chain.size(), output) ==
                    chain::Result::CYCLE && output.empty(),
            "long tail entering cycle rejects");
}

void sequenceTests() {
    std::size_t calls = 0;
    const auto occupied = [&calls](const int point) { ++calls; return point != 0; };
    const std::vector<int> empty;
    require(sequence::firstUnoccupiedIndex(empty, occupied) == 0 && calls == 0,
            "empty guide never dereferenced");
    for (const std::vector<int>& path : {
                 std::vector<int>{1}, std::vector<int>{1, 1, 1},
                 std::vector<int>{0}, std::vector<int>{1, 0, 1},
                 std::vector<int>{0, 1, 1}, std::vector<int>{1, 1, 0}}) {
        calls = 0;
        std::size_t expected = 0;
        while (expected < path.size() && path[expected] != 0) ++expected;
        const auto result = sequence::firstUnoccupiedIndex(path, occupied);
        require(result == expected, "first usable corridor seed matches legacy prefix");
        require(calls == (expected == path.size() ? path.size() : expected + 1),
                "occupied predicate evaluates exactly the original prefix");
        if (result < path.size()) require(path[result] == 0, "usable seed safe to index");
    }

    for (std::size_t count = 0; count < 100; ++count) {
        std::vector<int> samples;
        for (std::size_t i = 0; i < count; ++i) samples.push_back(static_cast<int>(i));
        const auto original = samples;
        const bool retained = sequence::discardTrailingSampleKeepingSeed(samples);
        require(retained == (count >= 2), "backup requires retained seed after drop");
        if (count < 2) {
            require(samples == original, "empty/singleton backup rejected without mutation");
        } else {
            require(samples.size() == count - 1 &&
                            samples.back() == static_cast<int>(count - 2),
                    "valid backup seed and sample sequence unchanged");
        }
    }
}
}  // namespace

int main() {
    try {
        parentChainTests();
        sequenceTests();
        std::cout << "planner_sequence_guards_test=PASS checks=" << checks << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "planner_sequence_guards_test=FAIL reason=" << error.what() << '\n';
        return 1;
    }
}
