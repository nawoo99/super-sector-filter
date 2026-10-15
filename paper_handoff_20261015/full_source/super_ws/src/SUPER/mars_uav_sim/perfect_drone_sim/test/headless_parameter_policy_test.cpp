#include "perfect_drone_sim/headless_parameter_policy.hpp"

#include <algorithm>
#include <chrono>
#include <iostream>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <thread>

namespace policy = perfect_drone::headless_parameter_policy;
using namespace std::chrono_literals;

namespace {
std::size_t checks = 0;

void require(const bool value, const std::string& message) {
  ++checks;
  if (!value) throw std::runtime_error(message);
}

std::set<std::string> parameterServices(
    const rclcpp::Node::SharedPtr& observer, const std::string& node) {
  std::set<std::string> result;
  const auto services = observer->get_service_names_and_types_by_node(node, "/");
  for (const auto& entry : services) result.insert(entry.first);
  return result;
}

std::set<std::string> expectedServices(const std::string& node) {
  std::set<std::string> result;
  for (const auto* suffix : {
           "describe_parameters", "get_parameter_types", "get_parameters",
           "list_parameters", "set_parameters", "set_parameters_atomically"}) {
    result.insert("/" + node + "/" + suffix);
  }
  return result;
}

bool eventPublisherPresent(const rclcpp::Node::SharedPtr& observer,
                           const std::string& node) {
  for (const auto& publisher :
       observer->get_publishers_info_by_topic("/parameter_events")) {
    if (publisher.node_name() == node && publisher.node_namespace() == "/")
      return true;
  }
  return false;
}
}  // namespace

int main(int argc, char** argv) {
  rclcpp::init(argc, argv);
  try {
    require(!policy::enabled(nullptr), "unset remains disabled");
    require(policy::enabled("1"), "exact opt-in");
    for (const auto* other : {"", "0"})
      require(!policy::enabled(other), "disabled spelling");
    for (const auto* other : {"true", "01", "1 ", " 1", "2", "-1"}) {
      bool rejected = false;
      try { (void)policy::enabled(other); }
      catch (const std::invalid_argument&) { rejected = true; }
      require(rejected, "unsupported nonempty spelling rejected");
    }

    rclcpp::NodeOptions base;
    base.use_intra_process_comms(true);
    base.parameter_overrides({rclcpp::Parameter("config_name", "seed1.yaml"),
                              rclcpp::Parameter("startup_value", 73)});
    const auto original_qos = base.parameter_event_qos().get_rmw_qos_profile();
    rclcpp::NodeOptions control_options(base);
    policy::apply(control_options, false);
    require(control_options.start_parameter_services(), "default services unchanged");
    require(control_options.start_parameter_event_publisher(), "default events unchanged");

    rclcpp::NodeOptions headless_options(base);
    policy::apply(headless_options, true);
    require(!headless_options.start_parameter_services(), "opt-in disables services");
    require(!headless_options.start_parameter_event_publisher(), "opt-in disables events");
    require(headless_options.use_intra_process_comms(), "intra-process setting preserved");
    require(headless_options.parameter_overrides().size() == 2,
            "startup override vector preserved");
    require(headless_options.parameter_event_qos().get_rmw_qos_profile().depth ==
                original_qos.depth, "parameter event QoS untouched");
    require(headless_options.clock_qos().get_rmw_qos_profile().depth ==
                base.clock_qos().get_rmw_qos_profile().depth, "clock QoS untouched");
    require(headless_options.enable_rosout() == base.enable_rosout(), "rosout untouched");
    policy::apply(headless_options, false);
    require(!headless_options.start_parameter_services() &&
                !headless_options.start_parameter_event_publisher(),
            "disabled helper does not reset caller-supplied settings");

    auto control = std::make_shared<rclcpp::Node>("cpu15_control", control_options);
    auto headless = std::make_shared<rclcpp::Node>("cpu15_headless", headless_options);
    auto observer = std::make_shared<rclcpp::Node>("cpu15_observer");
    for (const auto& node : {control, headless}) {
      require(node->declare_parameter<std::string>("config_name", "wrong.yaml") ==
                  "seed1.yaml", "local string override is effective");
      require(node->declare_parameter<int>("startup_value", -1) == 73,
              "local integer override is effective");
      require(node->get_parameter("config_name").as_string() == "seed1.yaml",
              "local get works");
      require(node->set_parameter(rclcpp::Parameter("startup_value", 91)).successful,
              "local set works");
      require(node->get_parameter("startup_value").as_int() == 91,
              "local set is visible");
    }

    rclcpp::executors::SingleThreadedExecutor executor;
    executor.add_node(control);
    executor.add_node(headless);
    executor.add_node(observer);
    const auto deadline = std::chrono::steady_clock::now() + 5s;
    bool control_graph_ready = false;
    do {
      executor.spin_some();
      const auto discovered_nodes = observer->get_node_names();
      control_graph_ready = parameterServices(observer, "cpu15_control") ==
                                expectedServices("cpu15_control") &&
                            eventPublisherPresent(observer, "cpu15_control") &&
                            std::find(discovered_nodes.begin(), discovered_nodes.end(),
                                      "/cpu15_headless") != discovered_nodes.end();
      if (control_graph_ready) break;
      std::this_thread::sleep_for(10ms);
    } while (std::chrono::steady_clock::now() < deadline);
    require(control_graph_ready,
            "default six services/event publisher and headless node discovered");
    require(parameterServices(observer, "cpu15_headless").empty(),
            "headless parameter service graph empty");
    require(!eventPublisherPresent(observer, "cpu15_headless"),
            "headless parameter event publisher absent");

    auto control_client = std::make_shared<rclcpp::AsyncParametersClient>(
        observer, "/cpu15_control");
    auto headless_client = std::make_shared<rclcpp::AsyncParametersClient>(
        observer, "/cpu15_headless");
    require(control_client->wait_for_service(2s), "default remote RPC service ready");
    auto future = control_client->get_parameters({"startup_value", "config_name"});
    require(executor.spin_until_future_complete(future, 3s) ==
                rclcpp::FutureReturnCode::SUCCESS, "default remote get RPC completes");
    const auto values = future.get();
    require(values.size() == 2 && values[0].as_int() == 91 &&
                values[1].as_string() == "seed1.yaml", "default remote values match");
    require(!headless_client->wait_for_service(250ms), "headless remote RPC unavailable");

    policy::reportEffectiveOptions(observer->get_logger(), "control", false,
                                   {control.get()});
    policy::reportEffectiveOptions(observer->get_logger(), "test", true,
                                   {headless.get()});
    std::cout << "headless_parameter_policy_test=PASS checks=" << checks
              << " local_override_declare_get_set=preserved "
              << "default_remote_services=6 headless_remote_services=0 "
              << "default_parameter_event_publishers=1 headless_parameter_event_publishers=0\n";
    rclcpp::shutdown();
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "headless_parameter_policy_test=FAIL checks=" << checks
              << " error=" << error.what() << '\n';
    rclcpp::shutdown();
    return 1;
  }
}
