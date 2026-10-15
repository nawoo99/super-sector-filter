#pragma once

// Opt-in observation only. No ROS/Eigen dependency and no planner feedback.
// The caller supplies JSON object members, without the surrounding braces.
// No filesystem work is done by submit(); one writer owns the exclusive file.
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <fcntl.h>
#include <iomanip>
#include <locale>
#include <memory>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <unistd.h>

namespace rog_map::contact_trace {

// Defaults reproduce the first G1 contact investigation.  A diagnostic run
// may select another already-observed contact cylinder without recompiling by
// setting SUPER_CONTACT_TRACE_CENTER_X/Y.  These values are observation-only:
// callers may use them to decide what to record, never for planner decisions.
inline constexpr double kCenterX = -28.591183;
inline constexpr double kCenterY = -4.598807;

inline double configuredCoordinate(const char* name, const double fallback) noexcept {
    const char* value = std::getenv(name);
    if (value == nullptr || value[0] == '\0') return fallback;
    char* end = nullptr;
    errno = 0;
    const double parsed = std::strtod(value, &end);
    return errno == 0 && end != value && *end == '\0' && std::isfinite(parsed)
                   ? parsed : fallback;
}

inline double centerX() noexcept {
    static const double value = configuredCoordinate(
            "SUPER_CONTACT_TRACE_CENTER_X", kCenterX);
    return value;
}

inline double centerY() noexcept {
    static const double value = configuredCoordinate(
            "SUPER_CONTACT_TRACE_CENTER_Y", kCenterY);
    return value;
}

inline bool inRoi(const double x, const double y, const double z) noexcept {
    const double center_x = centerX();
    const double center_y = centerY();
    return x >= center_x - 2.0 && x <= center_x + 2.0 &&
           y >= center_y - 2.0 && y <= center_y + 2.0 &&
           z >= -0.5 && z <= 3.5;
}

inline bool enabled() noexcept {
    static const bool value = []() noexcept {
        const char* directory = std::getenv("SUPER_G1_CONTACT_TRACE_DIR");
        return directory != nullptr && directory[0] != '\0';
    }();
    return value;
}

inline std::ostringstream stream() {
    std::ostringstream out;
    out.imbue(std::locale::classic());
    out << std::setprecision(17);
    return out;
}

inline std::string number(const double value) {
    if (!std::isfinite(value)) return "null";
    auto out = stream();
    out << value;
    return out.str();
}

namespace detail {

inline constexpr std::size_t kQueueCapacity = 4096;
inline constexpr std::size_t kQueueMemoryCap = 16 * 1024 * 1024;
inline constexpr std::size_t kRecordCap = 1024 * 1024;
inline constexpr std::size_t kFileCap = 256 * 1024 * 1024;
inline constexpr std::size_t kFooterReserve = 8192;

inline std::string quoted(const char* value) {
    std::string result = "\"";
    if (value != nullptr) {
        constexpr char hex[] = "0123456789abcdef";
        for (const unsigned char* p = reinterpret_cast<const unsigned char*>(value); *p; ++p) {
            if (*p == '"' || *p == '\\') {
                result += '\\';
                result += static_cast<char>(*p);
            } else if (*p < 0x20) {
                result += "\\u00";
                result += hex[*p >> 4];
                result += hex[*p & 15];
            } else {
                result += static_cast<char>(*p);
            }
        }
    }
    return result + '"';
}

inline std::int64_t epochNs() noexcept {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}

inline std::int64_t steadyNs() noexcept {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}

class Writer {
public:
    explicit Writer(std::string directory)
        : path_(std::move(directory) + "/contact_trace_" + std::to_string(::getpid()) + ".jsonl"),
          pid_(::getpid()), worker_([this]() { run(); }) {}

    Writer(const Writer&) = delete;
    Writer& operator=(const Writer&) = delete;

    ~Writer() noexcept {
        stopping_.store(true, std::memory_order_release);
        ready_.notify_one();
        if (worker_.joinable()) worker_.join();
    }

    void submit(const char* kind, const std::string& fields) noexcept {
        const auto sequence = submitted_.fetch_add(1, std::memory_order_relaxed) + 1;
        try {
            if (fields.size() > kRecordCap) {
                drop(record_drops_);
                return;
            }
            if (!accepting_.load(std::memory_order_acquire)) {
                drop(closed_drops_);
                return;
            }
            auto out = stream();
            out << "{\"kind\":" << quoted(kind) << ",\"epoch_ns\":" << epochNs()
                << ",\"steady_ns\":" << steadyNs() << ",\"sequence\":" << sequence
                << ",\"pid\":" << pid_;
            if (!fields.empty()) out << ',' << fields;
            out << "}\n";
            std::string record = out.str();
            if (record.size() > kRecordCap) {
                drop(record_drops_);
                return;
            }
            std::unique_lock<std::mutex> lock(mutex_, std::try_to_lock);
            if (!lock.owns_lock()) {
                drop(contention_drops_);
                return;
            }
            if (!accepting_.load(std::memory_order_acquire)) {
                drop(closed_drops_);
                return;
            }
            // Charge capacity and conservative per-record allocation overhead.
            const std::size_t charge = record.capacity() + sizeof(Entry) + 128;
            if (queue_.size() >= kQueueCapacity || charge > kQueueMemoryCap - queue_bytes_) {
                drop(queue_drops_);
                return;
            }
            queue_.push_back(Entry{std::move(record), charge});
            queue_bytes_ += charge;
            if (queue_.size() > peak_queue_records_) peak_queue_records_ = queue_.size();
            if (queue_bytes_ > peak_queue_bytes_) peak_queue_bytes_ = queue_bytes_;
            lock.unlock();
            ready_.notify_one();
        } catch (...) {
            drop(exception_drops_);
        }
    }

private:
    struct Entry { std::string record; std::size_t charge; };
    std::string path_;
    pid_t pid_;
    std::mutex mutex_;
    std::condition_variable ready_;
    std::deque<Entry> queue_;
    std::size_t queue_bytes_{0}, peak_queue_records_{0}, peak_queue_bytes_{0};
    std::atomic<bool> stopping_{false}, accepting_{true};
    std::atomic<std::uint64_t> submitted_{0}, dropped_{0};
    std::atomic<std::uint64_t> record_drops_{0}, queue_drops_{0}, contention_drops_{0};
    std::atomic<std::uint64_t> exception_drops_{0}, closed_drops_{0}, file_cap_drops_{0};
    std::uint64_t written_{0}, bytes_written_{0}, errors_{0}, checkpoints_{0};
    int fd_{-1};
    bool file_cap_reached_{false};
    // Declare thread last: its entry may execute before the constructor returns.
    std::thread worker_;

    void drop(std::atomic<std::uint64_t>& reason) noexcept {
        reason.fetch_add(1, std::memory_order_relaxed);
        dropped_.fetch_add(1, std::memory_order_relaxed);
    }

    bool writeBytes(const std::string& record) noexcept {
        const char* data = record.data();
        std::size_t left = record.size();
        while (left != 0) {
            const ssize_t amount = ::write(fd_, data, left);
            if (amount < 0 && errno == EINTR) continue;
            if (amount <= 0) {
                ++errors_;
                std::fprintf(stderr, "[G1_CONTACT_TRACE_ERROR] write path=%s errno=%d errors=%llu\n",
                             path_.c_str(), errno, static_cast<unsigned long long>(errors_));
                return false;
            }
            data += amount;
            left -= static_cast<std::size_t>(amount);
            bytes_written_ += static_cast<std::uint64_t>(amount);
        }
        return true;
    }

    std::string control(const char* kind) {
        std::size_t queued, queued_bytes, peak_records, peak_bytes;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            queued = queue_.size(); queued_bytes = queue_bytes_;
            peak_records = peak_queue_records_; peak_bytes = peak_queue_bytes_;
        }
        auto out = stream();
        out << "{\"kind\":" << quoted(kind) << ",\"schema\":\"g1-contact-trace-v1\""
            << ",\"epoch_ns\":" << epochNs() << ",\"steady_ns\":" << steadyNs()
            << ",\"sequence\":0,\"pid\":" << pid_
            << ",\"submitted\":" << submitted_.load() << ",\"written\":" << written_
            << ",\"dropped\":" << dropped_.load() << ",\"errors\":" << errors_
            << ",\"oversize_drops\":" << record_drops_.load()
            << ",\"queue_drops\":" << queue_drops_.load()
            << ",\"contention_drops\":" << contention_drops_.load()
            << ",\"exception_drops\":" << exception_drops_.load()
            << ",\"closed_drops\":" << closed_drops_.load()
            << ",\"file_cap_drops\":" << file_cap_drops_.load()
            << ",\"queued_records\":" << queued << ",\"queued_bytes\":" << queued_bytes
            << ",\"peak_queue_records\":" << peak_records << ",\"peak_queue_bytes\":" << peak_bytes
            << ",\"queue_record_cap\":" << kQueueCapacity << ",\"queue_memory_cap\":" << kQueueMemoryCap
            << ",\"record_byte_cap\":" << kRecordCap << ",\"file_byte_cap\":" << kFileCap
            << ",\"file_bytes_before_record\":" << bytes_written_
            << ",\"file_cap_reached\":" << (file_cap_reached_ ? "true" : "false")
            << ",\"checkpoints\":" << checkpoints_ << "}\n";
        return out.str();
    }

    void discardQueue() noexcept {
        std::lock_guard<std::mutex> lock(mutex_);
        while (!queue_.empty()) {
            queue_.pop_front();
            drop(closed_drops_);
        }
        queue_bytes_ = 0;
    }

    void run() noexcept {
        try {
            fd_ = ::open(path_.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
            if (fd_ < 0) {
                ++errors_;
                accepting_.store(false, std::memory_order_release);
                std::fprintf(stderr, "[G1_CONTACT_TRACE_ERROR] exclusive open failed path=%s errno=%d errors=%llu\n",
                             path_.c_str(), errno, static_cast<unsigned long long>(errors_));
                discardQueue();
                return;
            }
            bool healthy = writeBytes(control("trace_header"));
            auto checkpoint = std::chrono::steady_clock::now();
            while (healthy) {
                Entry entry;
                {
                    std::unique_lock<std::mutex> lock(mutex_);
                    ready_.wait_for(lock, std::chrono::milliseconds(250), [this]() {
                        return stopping_.load(std::memory_order_acquire) || !queue_.empty();
                    });
                    if (queue_.empty()) {
                        if (stopping_.load(std::memory_order_acquire)) break;
                    } else {
                        entry = std::move(queue_.front());
                        queue_.pop_front();
                        queue_bytes_ -= entry.charge;
                    }
                }
                if (!entry.record.empty()) {
                    if (bytes_written_ + entry.record.size() > kFileCap - kFooterReserve) {
                        file_cap_reached_ = true;
                        drop(file_cap_drops_);
                        accepting_.store(false, std::memory_order_release);
                        discardQueue();
                        // Stay alive until shutdown so the final counters also
                        // include submissions rejected after the file cap.
                        continue;
                    }
                    healthy = writeBytes(entry.record);
                    if (healthy) ++written_;
                    else drop(closed_drops_);
                }
                const auto now = std::chrono::steady_clock::now();
                if (healthy && now - checkpoint >= std::chrono::seconds(1)) {
                    ++checkpoints_;
                    const auto row = control("trace_checkpoint");
                    if (bytes_written_ + row.size() <= kFileCap - kFooterReserve)
                        healthy = writeBytes(row);
                    checkpoint = now;
                }
            }
            accepting_.store(false, std::memory_order_release);
            if (!healthy) discardQueue();
            const auto footer = control("trace_footer");
            if (bytes_written_ + footer.size() <= kFileCap) writeBytes(footer);
        } catch (...) {
            accepting_.store(false, std::memory_order_release);
            ++errors_;
            discardQueue();
            std::fprintf(stderr, "[G1_CONTACT_TRACE_ERROR] writer exception path=%s errors=%llu\n",
                         path_.c_str(), static_cast<unsigned long long>(errors_));
        }
        if (fd_ >= 0) ::close(fd_);
    }
};

inline Writer* writer() noexcept {
    static std::unique_ptr<Writer> value = []() noexcept -> std::unique_ptr<Writer> {
        try {
            const char* directory = std::getenv("SUPER_G1_CONTACT_TRACE_DIR");
            if (directory == nullptr || directory[0] == '\0') return nullptr;
            return std::make_unique<Writer>(directory);
        } catch (...) {
            std::fprintf(stderr, "[G1_CONTACT_TRACE_ERROR] writer initialization failed\n");
            return nullptr;
        }
    }();
    return value.get();
}

}  // namespace detail

inline void submit(const char* kind, const std::string& fields_json) noexcept {
    if (!enabled()) return;
    if (auto* output = detail::writer()) output->submit(kind, fields_json);
}

}  // namespace rog_map::contact_trace
