#include "static_map_edge_policy.hpp"
#include <cassert>
#include <iostream>

int main() {
  using static_map_edge::Policy;
  Policy p;
  auto d = p.observe({}, 0);
  assert(d.publish && d.initial);
  for (int i = 0; i < 100; ++i) assert(!p.observe({}, 0).publish);
  assert(!p.observe({"a"}, 0).publish);
  d = p.observe({"a"}, 1);
  assert(d.publish && d.new_reader && !d.initial);
  for (int i = 0; i < 100; ++i) assert(!p.observe({"a"}, 1).publish);
  assert(p.observe({"a", "b"}, 2).publish);
  assert(!p.observe({"a"}, 1).publish);  // Removal is not new map information.
  assert(p.observe({"c"}, 1).publish);  // Equal-count endpoint replacement.
  assert(!p.observe({}, 0).publish);
  assert(!p.observe({"d"}, 0).publish);
  assert(p.observe({"d"}, 1).publish);
  assert(p.observe({""}, 1).unsupported);
  assert(p.observe({"d"}, Policy::max_readers + 1).unsupported);
  std::set<std::string> too_many;
  for (std::size_t i = 0; i <= Policy::max_readers; ++i) too_many.insert(std::to_string(i));
  assert(p.observe(too_many, too_many.size()).unsupported);
  // No time input: ROS clock pause/rollback cannot generate an edge or loop.
  assert(!p.observe({"d"}, 1).publish);
  std::cout << "PASS static-map edge policy (not ROS transport proof)\n";
}
