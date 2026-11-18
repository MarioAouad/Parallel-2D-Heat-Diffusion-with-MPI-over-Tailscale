/*
 * Part 0, test 4: measure a message travelling rank 0 -> rank 1 -> rank 0.
 * This annotated source preserves the executable statements of the source
 * used for the archived measurements. The comments are teaching material.
 * Exactly TWO MPI processes participate, locally or on two different VMs.
 * MPI messages are application buffers; TCP/Tailscale handle network packets.
 * Read this folder's README for the timer boundaries and communication counts.
 */

// MPI supplies the communicator, point-to-point messages, collectives and timer.
#include <mpi.h>

// Standard-library tools used below: clamp/min/max and the payload check.
// array holds fixed-size names; vector owns a contiguous byte buffer;
// cstdint provides a wide traffic-budget integer; limits protects int parsing;
// cmath supplies ceil; iostream/iomanip produce CSV and diagnostic output;
// stdexcept/exception/new provide the validation and allocation error types.
// Some original includes are harmless even when not directly needed.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <new>
#include <stdexcept>
#include <string>
#include <vector>

// An anonymous namespace keeps helper names private to this source file.
// It does not create processes or network isolation.
namespace {
// 16 MiB = 16,777,216 bytes. We use powers of two to cover small startup-
// dominated messages and larger transfer-dominated messages. The size sweep
// contains 22 sizes: 2^3 through 2^24 inclusive, NOT 22 network packet sizes.
constexpr int maximum_bytes = 16 * 1024 * 1024;
// Allow one extra zero byte so gathered hostname slots remain null terminated.
constexpr int name_capacity = MPI_MAX_PROCESSOR_NAME + 1;

// Default run: 8 bytes through 16 MiB, one warm-up per size, adaptive measured
// repetitions. Zero iterations is an internal sentinel for automatic mode;
// explicit --iterations 0 is rejected to avoid division by zero. The label
// identifies a result case; it does not choose which VMs mpirun starts.
struct Options {
    int min_bytes = 8;
    int max_bytes = maximum_bytes;
    int iterations = 0; // Zero selects automatic repetition counts.
    int warmup = 1;
    std::string label = "pingpong";
    bool help = false;
};

// Convert an entire argument to a nonnegative int. stoll detects out-of-range
// input; used detects trailing junk. Reject negatives and values too large for
// MPI count and our int fields before any payload exchange starts.
int integer(const std::string& text) {
    std::size_t used = 0;
    const long long value = std::stoll(text, &used);
    if (used != text.size() || value < 0 ||
        value > std::numeric_limits<int>::max()) {
        throw std::invalid_argument("Invalid nonnegative integer: " + text);
    }
    return static_cast<int>(value);
}

// A positive power of two has exactly one set bit: clearing its lowest set bit
// with value & (value-1) leaves zero. Short-circuiting excludes zero/negatives.
bool power_of_two(int value) {
    return value > 0 && (value & (value - 1)) == 0;
}

// Each rank receives the same command line and independently parses it.
// Unknown flags or missing values are errors rather than silent defaults.
// The label whitelist prevents commas/newlines from breaking the CSV format.
// Selecting fewer sizes is allowed for a smoke test; full analysis requires all22.
Options parse(int argc, char** argv) {
    Options options;
    for (int i = 1; i < argc; ++i) {
        const std::string argument = argv[i];
        if (argument == "--help") {
            options.help = true;
            continue;
        }
        if (argument != "--min-bytes" && argument != "--max-bytes" &&
            argument != "--iterations" && argument != "--warmup" &&
            argument != "--label") {
            throw std::invalid_argument("Unknown option: " + argument);
        }
        if (++i == argc) {
            throw std::invalid_argument("Missing value for " + argument);
        }
        const std::string value = argv[i];
        if (argument == "--label") {
            if (value.empty() || value.find_first_not_of(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
                != std::string::npos) {
                throw std::invalid_argument("Label must use letters, digits, _, . or -");
            }
            options.label = value;
        } else if (argument == "--min-bytes") {
            options.min_bytes = integer(value);
        } else if (argument == "--max-bytes") {
            options.max_bytes = integer(value);
        } else if (argument == "--warmup") {
            options.warmup = integer(value);
        } else {
            options.iterations = integer(value);
            if (options.iterations == 0) {
                throw std::invalid_argument("--iterations must be positive when specified");
            }
        }
    }
    // Require a valid increasing range within the fixed maximum. Doubling bytes
    // later visits every requested power of two. The maximum also prevents overflow
    // in that loop: doubling 16 MiB to 32 MiB still fits a signed 32-bit int.
    if (!power_of_two(options.min_bytes) || !power_of_two(options.max_bytes) ||
        options.min_bytes < 8 || options.max_bytes > maximum_bytes ||
        options.min_bytes > options.max_bytes) {
        throw std::invalid_argument(
            "Sizes must be powers of two with 8 <= min <= max <= 16777216");
    }
    return options;
}

// One exchange is ONE round trip with TWO logical messages of bytes each.
// Rank 0 sends first while rank 1 receives first, then their roles reverse.
// If both ranks sent a large message first, blocking sends could wait forever.
// The vector is contiguous; MPI_BYTE means count is measured in bytes.
// Tags 10 (outbound) and 11 (reply) distinguish the directions in WORLD.
// These tag values are matching labels, not ports, sizes or performance knobs.
// Blocking completion permits the local buffer to be reused; it does not imply
// that MPI_Send alone measures complete delivery to the remote application.
void exchange(std::vector<unsigned char>& buffer, int bytes, int rank) {
    // The opposite send/receive order makes this safe for large messages too.
    if (rank == 0) {
        MPI_Send(buffer.data(), bytes, MPI_BYTE, 1, 10, MPI_COMM_WORLD);
        MPI_Recv(buffer.data(), bytes, MPI_BYTE, 1, 11, MPI_COMM_WORLD,
                 MPI_STATUS_IGNORE);
    } else {
        MPI_Recv(buffer.data(), bytes, MPI_BYTE, 0, 10, MPI_COMM_WORLD,
                 MPI_STATUS_IGNORE);
        MPI_Send(buffer.data(), bytes, MPI_BYTE, 0, 11, MPI_COMM_WORLD);
    }
}

// Choose a repetition count using rank 0's one-round-trip calibration.
// 0.2 seconds is a practical target to reduce tiny-timer overhead; it is not a
// hard runtime limit or a number demanded by the professor. MPI_Wtick guards
// against division by an effectively zero calibration interval. ceil rounds
// the desired count up; clamp enforces both the minimum and the traffic cap.
// The 64 MiB budget counts outgoing+return measured payloads (2*bytes per trip),
// not headers, barriers, warm-up or calibration. At 16 MiB, three repetitions
// already transfer 96 MiB; the minimum deliberately overrides the soft budget.
// The 10,000 cap avoids huge local loops. These choices trade measurement cost
// against stability and are documented rather than claimed universally optimal.
int automatic_iterations(int bytes, double pilot_roundtrip) {
    // Aim for 0.2 s of timing, capped at 10,000 repetitions and roughly
    // 64 MiB of measured traffic per size. Keep at least three repetitions.
    // Slow links / large messages can take longer than the target time.
    // Three is the minimum number of timed ROUND TRIPS at a size, not three
    // independent experiment sweeps. Large Internet messages can still take minutes.
    constexpr int minimum = 3;
    constexpr int maximum = 10000;
    constexpr std::int64_t traffic_budget = 64LL * 1024 * 1024;
    const int budget_limit = static_cast<int>(
        std::max<std::int64_t>(minimum, traffic_budget / (2LL * bytes)));
    const int limit = std::min(maximum, budget_limit);
    const double wanted = std::ceil(0.2 / std::max(pilot_roundtrip, MPI_Wtick()));
    return static_cast<int>(std::clamp(wanted, static_cast<double>(minimum),
                                     static_cast<double>(limit)));
}
} // namespace

// mpirun starts two copies of main. They take different branches using rank;
// MPI does not automatically parallelize an ordinary C++ loop.
int main(int argc, char** argv) {
    // Initialize MPI, then discover the local rank and communicator size.
    MPI_Init(&argc, &argv);
    int rank = 0;
    int size = 0;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    // Parse before allocating or communicating. Only rank 0 prints common errors
    // to avoid duplicated output; every process finalizes and exits on invalid input.
    Options options;
    try {
        options = parse(argc, argv);
    } catch (const std::exception& error) {
        if (rank == 0) std::cerr << "Error: " << error.what() << '\n';
        MPI_Finalize();
        return 2;
    }
    // Help exits without running a benchmark or creating result measurements.
    if (options.help) {
        if (rank == 0) {
            std::cout << "Run with exactly two MPI processes.\n"
                      << "Options: --min-bytes N --max-bytes N --iterations N "
                      << "--warmup N --label NAME\n"
                      << "Default: 8..16777216 bytes, automatic repetitions, "
                      << "one warm-up round trip per size.\n";
        }
        MPI_Finalize();
        return 0;
    }
    // This protocol has only endpoints 0 and 1. Six ranks are appropriate for hello,
    // not for this ping-pong program. Reject other sizes explicitly.
    if (size != 2) {
        if (rank == 0) std::cerr << "Error: use -np 2, not -np " << size << '\n';
        MPI_Finalize();
        return 2;
    }

    // Zero-initialized hostname slots are filled once, before measurement.
    // Allgather collects both names on both ranks; it is control/identification work,
    // not part of the timed point-to-point payload loop. Its internal message count
    // is implementation-dependent and is not included in our two-message formula.
    std::array<char, name_capacity> local_name{};
    std::array<char, 2 * name_capacity> names{};
    int length = 0;
    MPI_Get_processor_name(local_name.data(), &length);
    MPI_Allgather(local_name.data(), name_capacity, MPI_CHAR,
                  names.data(), name_capacity, MPI_CHAR, MPI_COMM_WORLD);
    // Allocate the largest buffer ONCE per rank. Rank 0 starts with the known
    // pattern 0x5a; rank 1 starts zeroed and overwrites its bytes on receive.
    // All tested payload sizes reuse prefixes of this buffer. Allocation failure
    // on one rank aborts the communicator rather than leaving its peer waiting.
    std::vector<unsigned char> buffer;
    try {
        buffer.assign(static_cast<std::size_t>(options.max_bytes),
                      rank == 0 ? 0x5a : 0x00);
    } catch (const std::bad_alloc&) {
        std::cerr << "Rank " << rank << ": unable to allocate message buffer\n";
        MPI_Abort(MPI_COMM_WORLD, 3);
        return 3;
    }

    // Only rank 0 writes measured CSV rows; stdout stays machine-readable.
    // Progress goes to stderr. Scientific precision preserves small local times.
    // The launcher stores these two streams separately.
    if (rank == 0) {
        std::cout << "label,host0,host1,bytes,iterations,warmup,roundtrip_s,oneway_s,effective_MiB_s\n"
                  << std::scientific << std::setprecision(12) << std::flush;
    }

    // Visit one size at a time; each rank executes the same sizes in the same order.
    // The first barrier aligns phases, then warm-up runs outside the reported timer.
    // A barrier synchronizes processes; it does not synchronize the VM clocks.
    for (int bytes = options.min_bytes; bytes <= options.max_bytes; bytes *= 2) {
        if (rank == 0) {
            std::cerr << "Testing " << bytes << " bytes: " << names.data()
                      << " <-> " << names.data() + name_capacity << '\n';
        }
        MPI_Barrier(MPI_COMM_WORLD);
        for (int i = 0; i < options.warmup; ++i) exchange(buffer, bytes, rank);

        // If adaptive mode is enabled, time one extra calibration round trip.
        // Only rank 0 selects the count; Bcast shares ONE MPI_INT with rank 1 so both
        // execute the same number of exchanges. A disagreement would hang the protocol.
        // With an explicit --iterations value, skip both calibration and this Bcast.
        int iterations = options.iterations;
        if (options.iterations == 0) {
            MPI_Barrier(MPI_COMM_WORLD);
            const double pilot_start = MPI_Wtime();
            exchange(buffer, bytes, rank);
            const double pilot_roundtrip = MPI_Wtime() - pilot_start;
            if (rank == 0) iterations = automatic_iterations(bytes, pilot_roundtrip);
            MPI_Bcast(&iterations, 1, MPI_INT, 0, MPI_COMM_WORLD);
        }

        // This barrier is immediately BEFORE the measured interval and is excluded.
        // Each rank has its own start/elapsed, but only rank 0's elapsed is reported.
        // Rank 0 times complete round trips on one clock, so cross-VM clock skew cannot
        // corrupt a subtraction between clocks. Timing includes MPI/library/scheduling
        // and transport costs; it is not a direct measurement of cable propagation.
        MPI_Barrier(MPI_COMM_WORLD);
        const double start = MPI_Wtime();
        for (int i = 0; i < iterations; ++i) exchange(buffer, bytes, rank);
        const double elapsed = MPI_Wtime() - start;

        if (rank == 0) {
            // Validation and printing are deliberately outside the timed loop.
            // Check the final returned buffer after timing, not once per iteration.
            // The constant pattern catches unexpected returned bytes; it is not a per-trip
            // sequence-number check and cannot prove each reply is fresh. MPI matching and
            // the blocking protocol provide ordering. No validation overhead is charged
            // to the measured loop.
            if (!std::all_of(buffer.begin(), buffer.begin() + bytes,
                             [](unsigned char value) { return value == 0x5a; })) {
                std::cerr << "Error: returned message is corrupted\n";
                MPI_Abort(MPI_COMM_WORLD, 4);
                return 4;
            }
            // Average RTT = measured loop seconds / round trips. Estimated one-way time
            // = RTT/2, assuming the two directions are comparable. It is NOT independently
            // measured directional latency. Effective MiB/s = message bytes / 2^20 / halfRTT;
            // equivalently 2*messageMiB/RTT. This includes startup overhead, so it differs
            // from bandwidth obtained from the slope of the large-message timing model.
            const double roundtrip = elapsed / iterations;
            const double oneway = roundtrip / 2.0;
            const double effective_bandwidth =
                (static_cast<double>(bytes) / (1024.0 * 1024.0)) / oneway;
            std::cout << options.label << ',' << names.data() << ','
                      << names.data() + name_capacity << ',' << bytes << ','
                      << iterations << ',' << options.warmup << ',' << roundtrip
                      << ',' << oneway << ',' << effective_bandwidth << '\n'
                      << std::flush;
        }
    }
    // This success marker is written only after every selected size finishes.
    // It does not certify numerical heat-solver correctness; no heat grid exists yet.
    if (rank == 0) std::cerr << "Finished successfully. CSV contains measured results.\n";
    // Finish collectively after the measurements. The launcher uses the normal
    // zero exit status to promote its partial CSV to a completed CSV.
    MPI_Finalize();
    return 0;
}
