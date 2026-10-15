// Standalone offline tests: g++ -std=c++17 -pthread -Irog_map/include this.cpp.
// Python's strict JSON decoder validates generated JSONL; no ROS is launched.
#include <rog_map/diagnostic_trace.hpp>

#include <cassert>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <sys/wait.h>
#include <vector>

namespace fs = std::filesystem;
namespace trace = rog_map::contact_trace;

static void require(const bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

static std::size_t threadCount() {
    return std::distance(fs::directory_iterator("/proc/self/task"), fs::directory_iterator{});
}

static int childMode(const std::string& mode, const fs::path& directory) {
    if (mode == "disabled") {
        ::unsetenv("SUPER_G1_CONTACT_TRACE_DIR");
        const auto before = threadCount();
        require(!trace::enabled(), "trace must default off");
        for (int n = 0; n < 100; ++n) trace::submit("disabled", "\"value\":1");
        require(threadCount() == before, "disabled mode created a thread");
        return 0;
    }
    ::setenv("SUPER_G1_CONTACT_TRACE_DIR", directory.c_str(), 1);
    require(trace::enabled(), "opt-in not enabled");
    if (mode == "exclusive") {
        std::ofstream existing(directory / ("contact_trace_" + std::to_string(::getpid()) + ".jsonl"));
        existing << "existing evidence\n";
        existing.close();
        trace::submit("must_not_overwrite", "\"value\":1");
        return 0;
    }
    if (mode == "open_error") {
        trace::submit("open_error", "\"value\":1");
        return 0;
    }
    require(trace::inRoi(trace::centerX(), trace::centerY(), 0.65), "ROI center rejected");
    require(!trace::inRoi(trace::centerX() + 2.01, trace::centerY(), 0.65), "ROI extent invalid");
    require(!trace::inRoi(trace::centerX(), trace::centerY(), 3.51), "ROI height invalid");
    require(!trace::inRoi(std::numeric_limits<double>::quiet_NaN(), trace::centerY(), 0.65), "NaN ROI accepted");
    if (mode == "normal") {
        for (int n = 0; n < 10; ++n) {
            auto fields = trace::stream();
            fields << "\"sample\":" << n << ",\"value\":" << trace::number(0.125)
                   << ",\"nan\":" << trace::number(std::numeric_limits<double>::quiet_NaN())
                   << ",\"inf\":" << trace::number(std::numeric_limits<double>::infinity());
            trace::submit("probe\"name\n", fields.str());
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
        }
        trace::submit("oversize", std::string(trace::detail::kRecordCap + 1, 'x'));
        // Exercise an actual asynchronous periodic checkpoint with no new rows.
        std::this_thread::sleep_for(std::chrono::milliseconds(1150));
    } else if (mode == "stress") {
        std::vector<std::thread> workers;
        const std::string payload = "\"payload\":\"" + std::string(4096, 'x') + "\"";
        for (int thread = 0; thread < 8; ++thread) {
            workers.emplace_back([&payload]() {
                for (int n = 0; n < 600; ++n) trace::submit("stress", payload);
            });
        }
        for (auto& worker : workers) worker.join();
    } else {
        throw std::runtime_error("Unknown child mode");
    }
    return 0;
}

static pid_t runChild(const char* executable, const std::string& mode, const fs::path& directory) {
    const pid_t pid = ::fork();
    require(pid >= 0, "fork failed");
    if (pid == 0) {
        ::execl(executable, executable, "--child", mode.c_str(), directory.c_str(), nullptr);
        ::_exit(127);
    }
    int status = 0;
    require(::waitpid(pid, &status, 0) == pid && WIFEXITED(status) && WEXITSTATUS(status) == 0,
            "child failed: " + mode);
    return pid;
}

static void checkJson(const fs::path& file, const std::string& mode) {
    static const char* script = R"PY(
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); mode=sys.argv[2]
def invalid(value): raise ValueError(value)
rows=[json.loads(line,parse_constant=invalid) for line in p.read_text().splitlines()]
assert rows[0]['kind']=='trace_header' and rows[-1]['kind']=='trace_footer'
footer=rows[-1]
data=[r for r in rows if not r['kind'].startswith('trace_')]
assert data and footer['written']==len(data)
assert footer['submitted']==footer['written']+footer['dropped']
assert footer['dropped']==sum(footer[k] for k in ('oversize_drops','queue_drops','contention_drops','exception_drops','closed_drops','file_cap_drops'))
assert footer['errors']==0 and footer['queued_records']==0 and footer['queued_bytes']==0
assert footer['peak_queue_records']<=4096 and footer['peak_queue_bytes']<=16*1024*1024
assert p.stat().st_size<=256*1024*1024
assert all(len(line.encode())+1<=1024*1024 for line in p.read_text().splitlines())
assert len({r['sequence'] for r in data})==len(data)
for r in rows:
 assert isinstance(r['pid'],int) and r['pid']>0
 assert isinstance(r['epoch_ns'],int) and r['epoch_ns']>0
 assert isinstance(r['steady_ns'],int) and r['steady_ns']>0
if mode=='normal':
 assert footer['submitted']==11 and footer['oversize_drops']==1
 assert footer['checkpoints']>=1 and any(r['kind']=='trace_checkpoint' for r in rows)
 assert all(r['kind']=='probe"name\n' and r['value']==.125 and r['nan'] is None and r['inf'] is None for r in data)
else: assert footer['submitted']==4800
print(mode,'written',footer['written'],'dropped',footer['dropped'],'peakbytes',footer['peak_queue_bytes'])
)PY";
    const pid_t pid = ::fork();
    require(pid >= 0, "fork JSON checker failed");
    if (pid == 0) {
        ::execlp("python3", "python3", "-c", script, file.c_str(), mode.c_str(), nullptr);
        ::_exit(127);
    }
    int status = 0;
    require(::waitpid(pid, &status, 0) == pid && WIFEXITED(status) && WEXITSTATUS(status) == 0,
            "strict JSON validation failed");
}

int main(int argc, char** argv) {
    try {
        if (argc == 4 && std::string(argv[1]) == "--child") return childMode(argv[2], argv[3]);
        char pattern[] = "/tmp/g1_trace_test_XXXXXX";
        char* created = ::mkdtemp(pattern);
        require(created != nullptr, "mkdtemp failed");
        const fs::path root(created);
        for (const char* name : {"disabled", "normal", "stress", "exclusive"}) fs::create_directory(root/name);
        runChild(argv[0], "disabled", root/"disabled");
        require(fs::is_empty(root/"disabled"), "disabled mode produced a file");
        for (const char* name : {"normal", "stress"}) {
            const auto pid = runChild(argv[0], name, root/name);
            checkJson(root/name/("contact_trace_" + std::to_string(pid) + ".jsonl"), name);
        }
        const auto exclusive_pid = runChild(argv[0], "exclusive", root/"exclusive");
        std::ifstream existing(root/"exclusive"/("contact_trace_" + std::to_string(exclusive_pid) + ".jsonl"));
        std::string contents((std::istreambuf_iterator<char>(existing)), std::istreambuf_iterator<char>());
        require(contents == "existing evidence\n", "exclusive-open protection failed");
        runChild(argv[0], "open_error", root/"absent_directory");
        require(!fs::exists(root/"absent_directory"), "logger silently created directory");
        std::cout << "PASS diagnostic trace offline tests; retained temporary evidence " << root << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
