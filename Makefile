# Run "make" at the repository root on EACH Ubuntu VM.
# mpic++ wraps the real C++ compiler with MPI headers/link libraries.
CXX := mpic++
# We use the MPI C interface from C++, not the obsolete MPI C++ wrapper classes.
CPPFLAGS += -DOMPI_SKIP_MPICXX=1
# C++17 enables std::clamp; O2 optimizes; warnings help catch mistakes.
# ffp-contract=off prepares consistent arithmetic for the later heat solver.
CXXFLAGS := -std=c++17 -O2 -ffp-contract=off -Wall -Wextra -Wpedantic

.PHONY: all verify-results analyze test-analysis
all: build/mpi_hello build/mpi_pingpong

# Order-only prerequisite: create the directory without rebuilding merely
# because another file changes the directory's modification time.
build/mpi_hello: part0/03-mpi-hello/mpi_hello.cpp | build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< -o $@

build/mpi_pingpong: part0/04-pingpong/mpi_pingpong.cpp | build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< -o $@

build:
	mkdir -p build

# These targets read archived data. They do not launch new MPI experiments.
verify-results:
	python3 part0/05-analysis/verify_results.py

analyze:
	python3 part0/05-analysis/analyze_pingpong.py part0/results/2026-11-17/*/*.csv --out part0/results/analysis

test-analysis:
	python3 -m unittest discover -s part0/05-analysis/tests -v
