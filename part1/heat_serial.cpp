// Serial FTCS reference. Keep the stencil's arithmetic order in later MPI code.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <set>
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
    bool demo = false, help = false;
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
Options parse(int argc, char** argv) {
    Options o;
    std::set<std::string> seen;
    for (int i = 1; i < argc; ++i) {
        const std::string key = argv[i];
        if (!seen.insert(key).second) throw std::invalid_argument("Duplicate option: " + key);
        if (key == "--help") { o.help = true; continue; }
        if (key == "--allow-unstable-demo") { o.demo = true; continue; }
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
        } else if (value != "serial")
            throw std::invalid_argument("Only --decomp serial is implemented in Part 1.");
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
    return o;
}
// i varies fastest, so rows at fixed j are contiguous.
std::size_t idx(int i, int j, std::size_t width) {
    return static_cast<std::size_t>(j) * width + static_cast<std::size_t>(i);
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
}
int main(int argc, char** argv) {
    try {
        const auto o = parse(argc, argv);
        if (o.help) {
            std::cout << "heat --case 1|2|V --N N --r R (--T T | --steps M)\n"
                         "     [--decomp serial] [--out field.bin]\n"
                         "Defaults: case=1 N=64 r=0.2 decomp=serial.\n"
                         "Task 6.7: --case 1 --steps M --r 0.2625 --allow-unstable-demo\n";
            return 0;
        }
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
            // Account for division rounding: effective r must not exceed the request.
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
        const std::size_t width = static_cast<std::size_t>(o.N)+1;
        if (width > std::vector<double>().max_size()/width)
            throw std::invalid_argument("Grid is too large for a contiguous array.");
        std::vector<double> old(width*width, 0.0);
        const double pi = std::acos(-1.0);
        if (o.test == "V") {
            for (int j=1; j<o.N; ++j)
                for (int i=1; i<o.N; ++i)
                    old[idx(i,j,width)] = std::sin(pi*i*h)*std::sin(pi*j*h);
        } else {
            if (o.test == "1")
                for (int j=0; j<=o.N; ++j)
                    old[idx(0,j,width)] = old[idx(o.N,j,width)] = 1.0;
            // Hot horizontal edges own the corners, including in Case 2.
            for (int i=0; i<=o.N; ++i)
                old[idx(i,0,width)] = old[idx(i,o.N,width)] = 1.0;
        }
        std::vector<double> next(old); // Initialize fixed boundaries in both buffers.
        if (o.demo) std::cerr << "Task 6.7: deliberately exceeding r <= 1/4.\n";
        const auto start = std::chrono::steady_clock::now();
        for (std::uint64_t n=0; n<steps; ++n) {
            for (int j=1; j<o.N; ++j) {
                for (int i=1; i<o.N; ++i) {
                    const auto k = idx(i,j,width);
                    const double sum = ((old[k-1]+old[k+1])+old[k-width])+old[k+width];
                    next[k] = old[k]+r*(sum-4.0*old[k]);
                }
            }
            old.swap(next);
        }
        const double elapsed = std::chrono::duration<double>(
            std::chrono::steady_clock::now()-start).count();
        // Error evaluation, range and I/O are excluded from the loop timer.
        double einf=0, sumsq=0;
        if (o.test == "V") {
            const double amplitude = std::exp(-2*pi*pi*final_time);
            for (int j=1; j<o.N; ++j) {
                for (int i=1; i<o.N; ++i) {
                    const double exact = std::sin(pi*i*h)*std::sin(pi*j*h)*amplitude;
                    const double error = old[idx(i,j,width)]-exact;
                    einf=std::max(einf,std::abs(error));
                    sumsq+=error*error;
                }
            }
        }
        const auto range = std::minmax_element(old.begin(),old.end());
        if (!o.output.empty()) write_field(o.output,old);
        std::cout << std::setprecision(17)
                  << "decomp=serial P=1 case=" << o.test << " N=" << o.N
                  << " steps=" << steps << " r=" << r << " dt=" << dt
                  << " T=" << final_time << " t_total=" << elapsed
                  << " t_comp=" << elapsed << " t_comm=0"
                  << " minimum=" << *range.first << " maximum=" << *range.second;
        if (o.test == "V") std::cout << " err_inf=" << einf << " err_l2=" << h*std::sqrt(sumsq);
        std::cout << '\n';
    } catch (const std::exception& error) {
        std::cerr << "Error: " << error.what() << '\n';
        return 1;
    }
}
