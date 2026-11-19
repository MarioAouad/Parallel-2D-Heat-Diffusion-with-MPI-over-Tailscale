#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

// Reference implementation for background-note Tasks 6.7 and 7.2.
// Build: g++ -std=c++17 -O3 -ffp-contract=off heat_serial.cpp -o heat_serial
int main(int argc, char** argv) {
    try {
        if (argc < 5) {
            std::cerr << "Usage: heat_serial N r T case [steps] [output.bin]\n"
                      << "case is V or 1; case X explicitly enables Task 6.7's unstable test.\n";
            return 1;
        }
        const int N = std::stoi(argv[1]);
        const double r_requested = std::stod(argv[2]);
        const double T = std::stod(argv[3]);
        const std::string test = argv[4];
        if (N < 2 || !(r_requested > 0) || !(T > 0))
            throw std::runtime_error("Require N >= 2, r > 0, T > 0.");
        if (test != "V" && test != "1" && test != "X")
            throw std::runtime_error("Unknown case.");
        if (r_requested > 0.25 && test != "X")
            throw std::runtime_error("Unstable r: the 2D five-point method requires r <= 1/4.");
        const double h = 1.0 / N;
        const bool fixed_steps = argc >= 6;
        const int steps = fixed_steps ? std::stoi(argv[5])
            : static_cast<int>(std::ceil(T / (r_requested * h * h)));
        if (steps < 1) throw std::runtime_error("Require positive steps.");
        const double dt = fixed_steps ? r_requested * h * h : T / steps;
        const double r = dt / (h * h);
        const double final_time = steps * dt;
        if (r > 0.25 && test != "X") throw std::runtime_error("Unstable effective r.");
        const int width = N + 1;
        auto idx = [width](int i, int j) { return static_cast<std::size_t>(j) * width + i; };
        std::vector<double> old(static_cast<std::size_t>(width) * width, 0.0), next(old);
        const double pi = std::acos(-1.0);
        if (test == "V") {
            for (int j = 1; j < N; ++j)
                for (int i = 1; i < N; ++i)
                    old[idx(i,j)] = std::sin(pi*i*h) * std::sin(pi*j*h);
        } else {
            for (int k = 0; k <= N; ++k)
                old[idx(0,k)] = old[idx(N,k)] = old[idx(k,0)] = old[idx(k,N)] = 1.0;
        }
        next = old; // In particular, initialize both buffers' fixed boundaries.
        const auto start = std::chrono::steady_clock::now();
        for (int n = 0; n < steps; ++n) {
            for (int j = 1; j < N; ++j) {
                for (int i = 1; i < N; ++i) {
                    const auto k = idx(i,j);
                    const double sum = ((old[k-1] + old[k+1]) + old[k-width]) + old[k+width];
                    next[k] = old[k] + r * (sum - 4.0*old[k]);
                }
            }
            old.swap(next);
        }
        const double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        double einf = 0, sumsq = 0;
        if (test == "V") {
            for (int j = 0; j <= N; ++j) {
                for (int i = 0; i <= N; ++i) {
                    const double exact = (i == 0 || i == N || j == 0 || j == N) ? 0.0
                        : std::sin(pi*i*h)*std::sin(pi*j*h)*std::exp(-2*pi*pi*final_time);
                    const double e = old[idx(i,j)] - exact;
                    einf = std::max(einf, std::abs(e)); sumsq += e*e;
                }
            }
        }
        const auto range = std::minmax_element(old.begin(), old.end());
        std::cout << std::setprecision(17) << "N=" << N << " steps=" << steps
                  << " r=" << r << " dt=" << dt << " T=" << final_time
                  << " err_inf=" << einf << " err_l2=" << h*std::sqrt(sumsq)
                  << " minimum=" << *range.first << " maximum=" << *range.second
                  << " seconds=" << elapsed << '\n';
        if (argc >= 7) {
            std::ofstream out(argv[6], std::ios::binary);
            if (!out) throw std::runtime_error("Cannot open output.");
            out.write(reinterpret_cast<const char*>(old.data()),
                      static_cast<std::streamsize>(old.size()*sizeof(double)));
            if (!out) throw std::runtime_error("Output write failed.");
        }
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
