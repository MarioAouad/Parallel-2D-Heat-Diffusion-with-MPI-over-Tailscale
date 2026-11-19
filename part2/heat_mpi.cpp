// Part 2: 1D strip decomposition of the Part 1 FTCS reference (part1/heat_serial.cpp).
//
// Bit-for-bit rule: the stencil expression, the initial/boundary values and the
// time-step selection below are copied unchanged from the serial reference. Every
// rank therefore performs exactly the same floating-point operations, in the same
// order, on the same values as the serial loop. Only WHERE a row is stored changes.
#include <mpi.h>

#include <algorithm>
#include <array>
#include <climits>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
struct Options {
    int N = 64;
    double r = 0.2;
    std::string test = "1", output;
    std::optional<double> T;
    std::optional<std::uint64_t> steps;
    bool demo = false, help = false, debug = false;
};
std::uint64_t integer(const std::string& text) {
    if (text.empty() || text.find_first_not_of("0123456789") != std::string::npos)
        throw std::invalid_argument("Expected unsigned decimal integer: " + text);
    return std::stoull(text);
}
double number(const std::string& text) {
    std::size_t used = 0;
    const double v = std::stod(text, &used);
    if (used != text.size() || !std::isfinite(v))
        throw std::invalid_argument("Expected finite number: " + text);
    return v;
}
// Same interface and validation as the serial reference; --decomp accepts strips.
Options parse(int argc, char** argv) {
    Options o;
    std::set<std::string> seen;
    for (int i = 1; i < argc; ++i) {
        const std::string key = argv[i];
        if (!seen.insert(key).second) throw std::invalid_argument("Duplicate option: " + key);
        if (key == "--help") { o.help = true; continue; }
        if (key == "--allow-unstable-demo") { o.demo = true; continue; }
        if (key == "--debug-print") { o.debug = true; continue; }
        if (key != "--N" && key != "--r" && key != "--case" && key != "--T" &&
            key != "--steps" && key != "--out" && key != "--decomp")
            throw std::invalid_argument("Unknown option: " + key);
        if (++i == argc) throw std::invalid_argument("Missing value for " + key);
        const std::string value = argv[i];
        if (key == "--N") {
            const auto n = integer(value);
            if (n < 2 || n >= static_cast<std::uint64_t>(std::numeric_limits<int>::max()))
                throw std::invalid_argument("--N must be between 2 and INT_MAX-1.");
            o.N = static_cast<int>(n);
        } else if (key == "--r") o.r = number(value);
        else if (key == "--T") o.T = number(value);
        else if (key == "--steps") o.steps = integer(value);
        else if (key == "--case") o.test = value;
        else if (key == "--out") {
            if (value.empty()) throw std::invalid_argument("--out cannot be empty.");
            o.output = value;
        } else if (value == "serial")
            throw std::invalid_argument("--decomp serial is the Part 1 reference: run build/heat.");
        else if (value == "blocks")
            throw std::invalid_argument("--decomp blocks is Part 3 and is not implemented yet.");
        else if (value != "strips")
            throw std::invalid_argument("--decomp must be strips for this executable.");
    }
    if (o.help) return o;
    if (o.test != "1" && o.test != "2" && o.test != "V")
        throw std::invalid_argument("--case must be 1, 2, or V.");
    if (!(o.r > 0)) throw std::invalid_argument("--r must be positive.");
    if (o.T.has_value() == o.steps.has_value())
        throw std::invalid_argument("Specify exactly one of --T and --steps.");
    if (o.T && !(*o.T > 0)) throw std::invalid_argument("--T must be positive.");
    if (o.steps && *o.steps == 0) throw std::invalid_argument("--steps must be positive.");
    if (o.demo && (o.test != "1" || !o.steps || o.r <= 0.25))
        throw std::invalid_argument("Unstable demo requires --case 1, --steps, and r > 1/4.");
    if (o.r > 0.25 && !o.demo)
        throw std::invalid_argument("Unstable r: the 2D five-point scheme requires r <= 1/4.");
    if (o.debug && o.N > 16)
        throw std::invalid_argument("--debug-print is limited to N <= 16 (it prints every value).");
    return o;
}

// Which interior rows a rank owns. The N-1 interior rows j=1..N-1 are split into
// contiguous strips; the first (N-1) mod P ranks get one extra row. Rank 0 owns
// the bottom strip (smallest j) and rank P-1 the top one (assignment section 6.1).
struct Strip { int first; int rows; };
Strip strip_of(int rank, int P, int N) {
    const int interior = N - 1, base = interior / P, extra = interior % P;
    return {1 + rank * base + std::min(rank, extra), base + (rank < extra ? 1 : 0)};
}

// Initial value of global node (i,j). Identical expressions to the serial code:
// V uses sin(pi*i*h)*sin(pi*j*h) inside and exactly 0 on the edges; Case 1 has
// four hot edges; Case 2 has hot top/bottom rows (they own the corners) and
// cold left/right columns.
double initial_value(const std::string& test, int i, int j, int N, double h, double pi) {
    if (test == "V")
        return (i > 0 && i < N && j > 0 && j < N) ? std::sin(pi*i*h)*std::sin(pi*j*h) : 0.0;
    if (j == 0 || j == N) return 1.0;
    if (test == "1" && (i == 0 || i == N)) return 1.0;
    return 0.0;
}

void write_field(const std::string& path, const std::vector<double>& field) {
    static_assert(sizeof(double) == 8 && std::numeric_limits<double>::is_iec559,
                  "Output requires IEEE-754 binary64.");
    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("Cannot open output: " + path);
    const std::uint16_t one = 1;
    unsigned char first = 0;
    std::memcpy(&first, &one, 1);
    for (std::size_t begin = 0; begin < field.size();) {
        const auto count = std::min<std::size_t>(field.size() - begin, 8192);
        if (first == 1) {
            out.write(reinterpret_cast<const char*>(field.data()+begin),
                      static_cast<std::streamsize>(count * 8));
        } else {
            for (std::size_t k = begin; k < begin+count; ++k) {
                std::array<char, 8> bytes{};
                std::memcpy(bytes.data(), &field[k], 8);
                std::reverse(bytes.begin(), bytes.end());
                out.write(bytes.data(), 8);
            }
        }
        begin += count;
    }
    out.close();
    if (!out) throw std::runtime_error("Output write failed: " + path);
}

// Collect one text block per rank on rank 0, in rank order (for --debug-print).
// Printing from every rank directly would interleave unpredictably in mpirun.
void print_in_rank_order(const std::string& text, int rank, int P) {
    int length = static_cast<int>(text.size());
    std::vector<int> lengths(P), offsets(P);
    MPI_Gather(&length, 1, MPI_INT, lengths.data(), 1, MPI_INT, 0, MPI_COMM_WORLD);
    std::string all;
    if (rank == 0) {
        int total = 0;
        for (int p = 0; p < P; ++p) { offsets[p] = total; total += lengths[p]; }
        all.resize(static_cast<std::size_t>(total));
    }
    MPI_Gatherv(text.data(), length, MPI_CHAR, rank == 0 ? &all[0] : nullptr,
                lengths.data(), offsets.data(), MPI_CHAR, 0, MPI_COMM_WORLD);
    if (rank == 0) std::cout << all << std::flush;
}

int run(int rank, int P, int argc, char** argv) {
    const auto o = parse(argc, argv);
    if (o.help) {
        if (rank == 0)
            std::cout << "mpirun -np P heat_mpi --decomp strips --case 1|2|V --N N --r R\n"
                         "        (--T T | --steps M) [--out field.bin] [--debug-print]\n"
                         "Defaults: case=1 N=64 r=0.2 decomp=strips. Requires N-1 >= P.\n"
                         "--debug-print (N<=16): show every rank's rows and ghost rows.\n";
        return 0;
    }
    // ---- Time-step selection: copied from the serial reference (same dt, r, steps). ----
    const double h = 1.0/o.N, h2 = h*h;
    std::uint64_t steps = o.steps.value_or(1);
    double dt = o.r*h2, r = o.r;
    if (o.T) {
        const long double required = std::ceil(static_cast<long double>(*o.T) /
            (static_cast<long double>(o.r)*h2));
        if (!std::isfinite(required) || required >=
            static_cast<long double>(std::numeric_limits<std::uint64_t>::max()))
            throw std::invalid_argument("Requested time requires too many steps.");
        steps = std::max<std::uint64_t>(1, static_cast<std::uint64_t>(required));
        dt = *o.T/static_cast<double>(steps);
        r = dt/h2;
        while (r > o.r) {
            if (steps == std::numeric_limits<std::uint64_t>::max())
                throw std::invalid_argument("Step count overflow.");
            ++steps;
            dt = *o.T/static_cast<double>(steps);
            r = dt/h2;
        }
    }
    const double final_time = o.T.value_or(static_cast<double>(steps)*dt);
    if (!(dt > 0) || !std::isfinite(dt) || !std::isfinite(final_time))
        throw std::invalid_argument("Time parameters exceed the supported finite range.");

    // ---- Decomposition. All checks here are identical on every rank, so an error
    // makes every rank stop before any communication (no rank is left waiting). ----
    const int N = o.N;
    if (N - 1 < P)
        throw std::invalid_argument("Strips need at least one interior row per process (N-1 >= P).");
    const std::size_t width = static_cast<std::size_t>(N)+1;
    if (width > std::vector<double>().max_size()/width)
        throw std::invalid_argument("Grid is too large for a contiguous array.");
    if (width > static_cast<std::size_t>(INT_MAX))
        throw std::invalid_argument("A row is too long for one MPI message count.");
    const bool gather = !o.output.empty() || o.test == "V";
    if (gather && width*width > static_cast<std::size_t>(INT_MAX))
        throw std::invalid_argument("Full-field gather exceeds MPI int counts; omit --out.");

    const Strip mine = strip_of(rank, P, N);
    const int rows = mine.rows;
    // Local storage: rows+2 contiguous rows of N+1 values.
    //   local row 0        = bottom ghost  (global row mine.first-1)
    //   local rows 1..rows = owned rows    (global rows mine.first .. mine.first+rows-1)
    //   local row rows+1   = top ghost     (global row mine.first+rows)
    // For rank 0 the bottom ghost IS the plate's boundary row j=0; for rank P-1 the
    // top ghost IS the boundary row j=N. They are never overwritten (MPI_PROC_NULL).
    const auto lidx = [width](int lr, int i) {
        return static_cast<std::size_t>(lr)*width + static_cast<std::size_t>(i);
    };
    const double pi = std::acos(-1.0);
    std::vector<double> old(static_cast<std::size_t>(rows+2)*width);
    for (int lr = 0; lr <= rows+1; ++lr)
        for (int i = 0; i <= N; ++i)
            old[lidx(lr, i)] = initial_value(o.test, i, mine.first-1+lr, N, h, pi);
    std::vector<double> next(old);   // fixed boundaries (and ghost layout) in both buffers

    // Neighbours. MPI_PROC_NULL makes a send/receive a no-op, so the same code runs
    // on every rank with no special case for the bottom and top strips.
    const int down = rank > 0 ? rank-1 : MPI_PROC_NULL;
    const int up = rank < P-1 ? rank+1 : MPI_PROC_NULL;
    const int count = static_cast<int>(width);   // one full row = N+1 doubles, no packing
    const auto exchange = [&](std::vector<double>& u) {
        // Shift up: my top owned row goes to the rank above (its bottom ghost);
        // at the same time I receive my bottom ghost from the rank below.
        MPI_Sendrecv(&u[lidx(rows, 0)], count, MPI_DOUBLE, up, 0,
                     &u[lidx(0, 0)], count, MPI_DOUBLE, down, 0,
                     MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        // Shift down: my bottom owned row goes to the rank below (its top ghost);
        // at the same time I receive my top ghost from the rank above.
        MPI_Sendrecv(&u[lidx(1, 0)], count, MPI_DOUBLE, down, 1,
                     &u[lidx(rows+1, 0)], count, MPI_DOUBLE, up, 1,
                     MPI_COMM_WORLD, MPI_STATUS_IGNORE);
    };

    // ---- Time stepping: exchange halos, then the unchanged serial stencil. ----
    MPI_Barrier(MPI_COMM_WORLD);   // start every rank's clock together
    double t_comm = 0, t_comp = 0;
    const double t_start = MPI_Wtime();
    for (std::uint64_t n = 0; n < steps; ++n) {
        const double a = MPI_Wtime();
        exchange(old);
        const double b = MPI_Wtime();
        for (int lr = 1; lr <= rows; ++lr) {
            for (int i = 1; i < N; ++i) {
                const auto k = lidx(lr, i);
                const double sum = ((old[k-1]+old[k+1])+old[k-width])+old[k+width];
                next[k] = old[k]+r*(sum-4.0*old[k]);
            }
        }
        const double c = MPI_Wtime();
        old.swap(next);
        t_comm += b-a;
        t_comp += c-b;
    }
    const double t_total = MPI_Wtime()-t_start;
    // Report the slowest rank for each timer (assignment: MPI_Reduce with MPI_MAX).
    const double local_times[3] = {t_total, t_comp, t_comm};
    double max_times[3] = {0, 0, 0};
    MPI_Reduce(local_times, max_times, 3, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    // ---- Everything below is outside the timed loop. ----
    // Global minimum/maximum: owned rows, plus the boundary rows held as ghosts by
    // the first and last ranks. Min/max involve no rounding, so they equal serial.
    const int lo = rank == 0 ? 0 : 1, hi = rank == P-1 ? rows+1 : rows;
    const auto range = std::minmax_element(old.begin()+static_cast<std::ptrdiff_t>(lidx(lo, 0)),
                                           old.begin()+static_cast<std::ptrdiff_t>(lidx(hi+1, 0)));
    double local_min = *range.first, local_max = *range.second, gmin = 0, gmax = 0;
    MPI_Reduce(&local_min, &gmin, 1, MPI_DOUBLE, MPI_MIN, 0, MPI_COMM_WORLD);
    MPI_Reduce(&local_max, &gmax, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    // How many distinct machines took part (evidence for "across at least two VMs").
    std::array<char, MPI_MAX_PROCESSOR_NAME> name{};
    int name_length = 0;
    MPI_Get_processor_name(name.data(), &name_length);
    std::vector<char> names(rank == 0 ? static_cast<std::size_t>(P)*MPI_MAX_PROCESSOR_NAME : 1);
    MPI_Gather(name.data(), MPI_MAX_PROCESSOR_NAME, MPI_CHAR, names.data(),
               MPI_MAX_PROCESSOR_NAME, MPI_CHAR, 0, MPI_COMM_WORLD);

    // Rank 0 assembles the full field: each rank's owned rows land at their global
    // row offset; boundary rows j=0 and j=N are filled directly on rank 0.
    std::vector<double> full;
    if (gather) {
        std::vector<int> counts(P), displs(P);
        for (int p = 0; p < P; ++p) {
            const Strip s = strip_of(p, P, N);
            counts[p] = static_cast<int>(static_cast<std::size_t>(s.rows)*width);
            displs[p] = static_cast<int>(static_cast<std::size_t>(s.first)*width);
        }
        if (rank == 0) {
            full.assign(width*width, 0.0);
            for (int j : {0, N})
                for (int i = 0; i <= N; ++i)
                    full[static_cast<std::size_t>(j)*width+static_cast<std::size_t>(i)] =
                        initial_value(o.test, i, j, N, h, pi);
        }
        MPI_Gatherv(&old[lidx(1, 0)], counts[rank], MPI_DOUBLE,
                    rank == 0 ? full.data() : nullptr, counts.data(), displs.data(),
                    MPI_DOUBLE, 0, MPI_COMM_WORLD);
    }

    if (o.debug) {
        exchange(old);   // refresh ghosts so they show the neighbours' final rows
        std::ostringstream text;
        text << std::fixed << std::setprecision(6)
             << "rank " << rank << ": owns global rows " << mine.first << ".."
             << mine.first+rows-1 << " (" << rows << " rows), down="
             << (down == MPI_PROC_NULL ? std::string("none") : std::to_string(down))
             << " up=" << (up == MPI_PROC_NULL ? std::string("none") : std::to_string(up)) << '\n';
        for (int lr = rows+1; lr >= 0; --lr) {
            const int j = mine.first-1+lr;
            const bool ghost = lr == 0 || lr == rows+1;
            const bool edge = (lr == 0 && down == MPI_PROC_NULL) || (lr == rows+1 && up == MPI_PROC_NULL);
            text << (ghost ? (edge ? "  boundary" : "  ghost   ") : "  owned   ") << " j=" << std::setw(2) << j << ":";
            for (int i = 0; i <= N; ++i) text << ' ' << old[lidx(lr, i)];
            text << '\n';
        }
        print_in_rank_order(text.str(), rank, P);
    }

    if (rank != 0) return 0;
    std::set<std::string> hosts;
    for (int p = 0; p < P; ++p)
        hosts.insert(std::string(names.data()+static_cast<std::size_t>(p)*MPI_MAX_PROCESSOR_NAME));

    // Error norms on the assembled field, same loop order as the serial reference,
    // so err_inf and err_l2 are bit-identical to serial as well.
    double einf = 0, sumsq = 0;
    if (o.test == "V") {
        const double amplitude = std::exp(-2*pi*pi*final_time);
        for (int j = 1; j < N; ++j) {
            for (int i = 1; i < N; ++i) {
                const double exact = std::sin(pi*i*h)*std::sin(pi*j*h)*amplitude;
                const double error = full[static_cast<std::size_t>(j)*width+static_cast<std::size_t>(i)]-exact;
                einf = std::max(einf, std::abs(error));
                sumsq += error*error;
            }
        }
    }
    if (!o.output.empty()) write_field(o.output, full);
    std::cout << std::setprecision(17)
              << "decomp=strips P=" << P << " nodes=" << hosts.size()
              << " case=" << o.test << " N=" << N
              << " steps=" << steps << " r=" << r << " dt=" << dt
              << " T=" << final_time << " t_total=" << max_times[0]
              << " t_comp=" << max_times[1] << " t_comm=" << max_times[2]
              << " minimum=" << gmin << " maximum=" << gmax;
    if (o.test == "V") std::cout << " err_inf=" << einf << " err_l2=" << h*std::sqrt(sumsq);
    std::cout << '\n';
    return 0;
}
}  // namespace

int main(int argc, char** argv) {
    MPI_Init(&argc, &argv);
    int rank = 0, P = 1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &P);
    int status = 0;
    try {
        status = run(rank, P, argc, argv);
    } catch (const std::exception& error) {
        // Input errors are detected identically on every rank; print once.
        if (rank == 0) std::cerr << "Error: " << error.what() << '\n';
        status = 1;
    }
    MPI_Finalize();
    return status;
}
