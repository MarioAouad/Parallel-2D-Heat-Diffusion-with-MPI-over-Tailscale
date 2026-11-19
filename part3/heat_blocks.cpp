// Part 3: 2D block decomposition of the Part 1 FTCS reference (part1/heat_serial.cpp).
//
// Bit-for-bit rule (as in Part 2): the stencil expression, the initial/boundary values
// and the time-step selection are copied unchanged from the serial reference. Every
// node is computed from the same five values with the same operations in the same
// order; a block boundary only changes WHERE a value is stored.
//
// Grid of processes: MPI_Dims_create + MPI_Cart_create (non-periodic). Dimension 0 is
// y (rows, index j), dimension 1 is x (columns, index i). Rows of a block are
// contiguous and are sent directly; columns are strided and are sent with an
// MPI_Type_vector derived datatype (no hand-written packing).
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
// Same interface and validation as the serial reference; --decomp accepts blocks.
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
        else if (value == "strips")
            throw std::invalid_argument("--decomp strips is Part 2: run build/heat_mpi.");
        else if (value != "blocks")
            throw std::invalid_argument("--decomp must be blocks for this executable.");
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

// Even split of the N-1 interior indices 1..N-1 among `parts` processes, exactly as
// the Part 2 strips: contiguous ranges, the first (N-1) mod parts get one extra.
// Used for rows (over the y coordinate) and for columns (over the x coordinate).
struct Range { int first; int count; };
Range split(int part, int parts, int N) {
    const int interior = N - 1, base = interior / parts, extra = interior % parts;
    return {1 + part * base + std::min(part, extra), base + (part < extra ? 1 : 0)};
}

// Initial value of global node (i,j): identical expressions to the serial code.
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
void print_in_rank_order(const std::string& text, int rank, int P, MPI_Comm comm) {
    int length = static_cast<int>(text.size());
    std::vector<int> lengths(P), offsets(P);
    MPI_Gather(&length, 1, MPI_INT, lengths.data(), 1, MPI_INT, 0, comm);
    std::string all;
    if (rank == 0) {
        int total = 0;
        for (int p = 0; p < P; ++p) { offsets[p] = total; total += lengths[p]; }
        all.resize(static_cast<std::size_t>(total));
    }
    MPI_Gatherv(text.data(), length, MPI_CHAR, rank == 0 ? &all[0] : nullptr,
                lengths.data(), offsets.data(), MPI_CHAR, 0, comm);
    if (rank == 0) std::cout << all << std::flush;
}

std::string neighbour(int r) { return r == MPI_PROC_NULL ? std::string("none") : std::to_string(r); }

int run(int rank, int P, int argc, char** argv) {
    const auto o = parse(argc, argv);
    if (o.help) {
        if (rank == 0)
            std::cout << "mpirun -np P heat_blocks --decomp blocks --case 1|2|V --N N --r R\n"
                         "        (--T T | --steps M) [--out field.bin] [--debug-print]\n"
                         "Defaults: case=1 N=64 r=0.2 decomp=blocks. The Py x Px process grid comes\n"
                         "from MPI_Dims_create; N-1 must be >= Py and >= Px.\n"
                         "--debug-print (N<=16): show every block with its ghost rows and columns.\n";
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

    // ---- Process grid. All checks are identical on every rank (no rank left waiting). ----
    const int N = o.N;
    int dims[2] = {0, 0};
    MPI_Dims_create(P, 2, dims);              // balanced factorisation, dims[0] >= dims[1]
    const int Py = dims[0], Px = dims[1];     // Py block rows (y), Px block columns (x)
    if (N - 1 < Py || N - 1 < Px)
        throw std::invalid_argument("Blocks need at least one interior row and column per process: "
                                    "N-1 >= " + std::to_string(Py) + " for a " + std::to_string(Py) +
                                    "x" + std::to_string(Px) + " process grid.");
    const std::size_t width = static_cast<std::size_t>(N)+1;
    if (width > std::vector<double>().max_size()/width)
        throw std::invalid_argument("Grid is too large for a contiguous array.");
    const bool gather = !o.output.empty() || o.test == "V";

    const int periods[2] = {0, 0};            // non-periodic: plate edges get MPI_PROC_NULL
    MPI_Comm cart;
    // reorder=0 keeps cart rank == world rank, so rank 0 stays on the launching VM
    // (it writes the output file there).
    MPI_Cart_create(MPI_COMM_WORLD, 2, dims, periods, 0, &cart);
    int coords[2] = {0, 0};
    MPI_Cart_coords(cart, rank, 2, coords);
    int down = MPI_PROC_NULL, up = MPI_PROC_NULL, left = MPI_PROC_NULL, right = MPI_PROC_NULL;
    MPI_Cart_shift(cart, 0, 1, &down, &up);     // y direction: smaller j below, larger j above
    MPI_Cart_shift(cart, 1, 1, &left, &right);  // x direction: smaller i left, larger i right

    const Range ry = split(coords[0], Py, N), rx = split(coords[1], Px, N);
    const int rows = ry.count, cols = rx.count;
    // Local storage: (rows+2) x (cols+2), row-major, one ghost layer on all four sides.
    //   local (lr, li) <-> global (i, j) = (rx.first-1+li, ry.first-1+lr)
    // On a plate edge the ghost layer IS the Dirichlet boundary; it is never overwritten.
    // The four local corner cells are never exchanged: the five-point stencil never reads them.
    const std::size_t lw = static_cast<std::size_t>(cols)+2;
    const auto lidx = [lw](int lr, int li) {
        return static_cast<std::size_t>(lr)*lw + static_cast<std::size_t>(li);
    };
    const double pi = std::acos(-1.0);
    std::vector<double> old(static_cast<std::size_t>(rows+2)*lw);
    for (int lr = 0; lr <= rows+1; ++lr)
        for (int li = 0; li <= cols+1; ++li)
            old[lidx(lr, li)] = initial_value(o.test, rx.first-1+li, ry.first-1+lr, N, h, pi);
    std::vector<double> next(old);   // fixed boundaries in both buffers

    // One column of the owned block: `rows` doubles, each lw doubles apart in memory.
    MPI_Datatype column;
    MPI_Type_vector(rows, 1, static_cast<int>(lw), MPI_DOUBLE, &column);
    MPI_Type_commit(&column);

    const auto exchange = [&](std::vector<double>& u) {
        // Rows are contiguous: send the `cols` owned values directly from the array.
        // Shift up: my top owned row -> rank above; my bottom ghost row <- rank below.
        MPI_Sendrecv(&u[lidx(rows, 1)], cols, MPI_DOUBLE, up, 0,
                     &u[lidx(0, 1)], cols, MPI_DOUBLE, down, 0, cart, MPI_STATUS_IGNORE);
        // Shift down: my bottom owned row -> rank below; my top ghost row <- rank above.
        MPI_Sendrecv(&u[lidx(1, 1)], cols, MPI_DOUBLE, down, 1,
                     &u[lidx(rows+1, 1)], cols, MPI_DOUBLE, up, 1, cart, MPI_STATUS_IGNORE);
        // Columns are strided: one element of the derived `column` type each.
        // Shift right: my rightmost owned column -> right rank; my left ghost column <- left rank.
        MPI_Sendrecv(&u[lidx(1, cols)], 1, column, right, 2,
                     &u[lidx(1, 0)], 1, column, left, 2, cart, MPI_STATUS_IGNORE);
        // Shift left: my leftmost owned column -> left rank; my right ghost column <- right rank.
        MPI_Sendrecv(&u[lidx(1, 1)], 1, column, left, 3,
                     &u[lidx(1, cols+1)], 1, column, right, 3, cart, MPI_STATUS_IGNORE);
    };

    // ---- Time stepping: exchange halos, then the unchanged serial stencil. ----
    MPI_Barrier(cart);
    double t_comm = 0, t_comp = 0;
    const double t_start = MPI_Wtime();
    for (std::uint64_t n = 0; n < steps; ++n) {
        const double a = MPI_Wtime();
        exchange(old);
        const double b = MPI_Wtime();
        for (int lr = 1; lr <= rows; ++lr) {
            for (int li = 1; li <= cols; ++li) {
                const auto k = lidx(lr, li);
                const double sum = ((old[k-1]+old[k+1])+old[k-lw])+old[k+lw];
                next[k] = old[k]+r*(sum-4.0*old[k]);
            }
        }
        const double c = MPI_Wtime();
        old.swap(next);
        t_comm += b-a;
        t_comp += c-b;
    }
    const double t_total = MPI_Wtime()-t_start;
    const double local_times[3] = {t_total, t_comp, t_comm};
    double max_times[3] = {0, 0, 0};
    MPI_Reduce(local_times, max_times, 3, MPI_DOUBLE, MPI_MAX, 0, cart);

    // ---- Everything below is outside the timed loop. ----
    // Global min/max: owned block plus the boundary ghost layers on plate edges (incl. the
    // plate corners held by the corner blocks). Together these cover every node once.
    const int r0 = down == MPI_PROC_NULL ? 0 : 1, r1 = up == MPI_PROC_NULL ? rows+1 : rows;
    const int c0 = left == MPI_PROC_NULL ? 0 : 1, c1 = right == MPI_PROC_NULL ? cols+1 : cols;
    double local_min = std::numeric_limits<double>::infinity(), local_max = -local_min;
    for (int lr = r0; lr <= r1; ++lr)
        for (int li = c0; li <= c1; ++li) {
            local_min = std::min(local_min, old[lidx(lr, li)]);
            local_max = std::max(local_max, old[lidx(lr, li)]);
        }
    double gmin = 0, gmax = 0;
    MPI_Reduce(&local_min, &gmin, 1, MPI_DOUBLE, MPI_MIN, 0, cart);
    MPI_Reduce(&local_max, &gmax, 1, MPI_DOUBLE, MPI_MAX, 0, cart);

    std::array<char, MPI_MAX_PROCESSOR_NAME> name{};
    int name_length = 0;
    MPI_Get_processor_name(name.data(), &name_length);
    std::vector<char> names(rank == 0 ? static_cast<std::size_t>(P)*MPI_MAX_PROCESSOR_NAME : 1);
    MPI_Gather(name.data(), MPI_MAX_PROCESSOR_NAME, MPI_CHAR, names.data(),
               MPI_MAX_PROCESSOR_NAME, MPI_CHAR, 0, cart);

    // Rank 0 assembles the full field. Blocks are not contiguous in the global array, so
    // each transfer uses subarray datatypes on both sides (still no hand-written packing).
    std::vector<double> full;
    if (gather) {
        MPI_Datatype owned;
        const int lsizes[2] = {rows+2, cols+2}, lsub[2] = {rows, cols}, lstart[2] = {1, 1};
        MPI_Type_create_subarray(2, lsizes, lsub, lstart, MPI_ORDER_C, MPI_DOUBLE, &owned);
        MPI_Type_commit(&owned);
        if (rank == 0) {
            full.assign(width*width, 0.0);
            for (int j = 0; j <= N; ++j)
                for (int i = 0; i <= N; ++i)
                    if (i == 0 || i == N || j == 0 || j == N)
                        full[static_cast<std::size_t>(j)*width+static_cast<std::size_t>(i)] =
                            initial_value(o.test, i, j, N, h, pi);
            std::vector<MPI_Datatype> types(P);
            std::vector<MPI_Request> requests;
            for (int p = 0; p < P; ++p) {
                int c[2] = {0, 0};
                MPI_Cart_coords(cart, p, 2, c);
                const Range by = split(c[0], Py, N), bx = split(c[1], Px, N);
                const int gsizes[2] = {N+1, N+1}, gsub[2] = {by.count, bx.count},
                          gstart[2] = {by.first, bx.first};
                MPI_Type_create_subarray(2, gsizes, gsub, gstart, MPI_ORDER_C, MPI_DOUBLE, &types[p]);
                MPI_Type_commit(&types[p]);
                if (p == 0) {
                    MPI_Sendrecv(old.data(), 1, owned, 0, 9, full.data(), 1, types[0], 0, 9,
                                 cart, MPI_STATUS_IGNORE);
                } else {
                    requests.emplace_back();
                    MPI_Irecv(full.data(), 1, types[p], p, 9, cart, &requests.back());
                }
            }
            MPI_Waitall(static_cast<int>(requests.size()), requests.data(), MPI_STATUSES_IGNORE);
            for (auto& t : types) MPI_Type_free(&t);
        } else {
            MPI_Send(old.data(), 1, owned, 0, 9, cart);
        }
        MPI_Type_free(&owned);
    }

    if (o.debug) {
        exchange(old);   // refresh ghosts so they show the neighbours' final values
        std::ostringstream text;
        text << std::fixed << std::setprecision(6)
             << "rank " << rank << ": coords (" << coords[0] << "," << coords[1] << ") of "
             << Py << "x" << Px << " grid, rows " << ry.first << ".." << ry.first+rows-1
             << ", cols " << rx.first << ".." << rx.first+cols-1
             << ", down=" << neighbour(down) << " up=" << neighbour(up)
             << " left=" << neighbour(left) << " right=" << neighbour(right) << '\n';
        for (int lr = rows+1; lr >= 0; --lr) {
            const bool ghost_row = lr == 0 || lr == rows+1;
            const bool edge_row = (lr == 0 && down == MPI_PROC_NULL) || (lr == rows+1 && up == MPI_PROC_NULL);
            text << (ghost_row ? (edge_row ? "  boundary" : "  ghost   ") : "  owned   ")
                 << " j=" << std::setw(2) << ry.first-1+lr << ":";
            for (int li = 0; li <= cols+1; ++li) {
                const bool ghost_col = li == 0 || li == cols+1;
                if (ghost_row && ghost_col) text << "       -";   // corner: never exchanged
                else text << ' ' << old[lidx(lr, li)];
            }
            text << '\n';
        }
        print_in_rank_order(text.str(), rank, P, cart);
    }

    MPI_Type_free(&column);
    MPI_Comm_free(&cart);
    if (rank != 0) return 0;
    std::set<std::string> hosts;
    for (int p = 0; p < P; ++p)
        hosts.insert(std::string(names.data()+static_cast<std::size_t>(p)*MPI_MAX_PROCESSOR_NAME));

    // Error norms on the assembled field, in the serial loop order (bit-identical to serial).
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
              << "decomp=blocks P=" << P << " Py=" << Py << " Px=" << Px << " nodes=" << hosts.size()
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
        if (rank == 0) std::cerr << "Error: " << error.what() << '\n';
        status = 1;
    }
    MPI_Finalize();
    return status;
}
