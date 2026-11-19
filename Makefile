# Run "make" at the repository root on EACH Ubuntu VM.
# mpic++ wraps the real C++ compiler with MPI headers/link libraries.
CXX := mpic++
SERIAL_CXX ?= g++
# We use the MPI C interface from C++, not the obsolete MPI C++ wrapper classes.
CPPFLAGS += -DOMPI_SKIP_MPICXX=1
# C++17 enables std::clamp; O2 optimizes; warnings help catch mistakes.
# ffp-contract=off prepares consistent arithmetic for the later heat solver.
CXXFLAGS := -std=c++17 -O2 -ffp-contract=off -Wall -Wextra -Wpedantic

.PHONY: all serial verify-results verify-setup analyze test-analysis check-serial verify-part1
all: build/mpi_hello build/mpi_pingpong build/heat

serial: build/heat

build/heat: part1/heat_serial.cpp | build
	$(SERIAL_CXX) $(CXXFLAGS) $< -o $@

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

verify-setup:
	python3 part0/05-analysis/verify_setup.py

check-serial: build/heat
	python3 part1/verify_serial.py --exe build/heat

verify-part1: build/heat
	python3 part1/run_experiments.py --exe build/heat

analyze:
	python3 part0/05-analysis/analyze_pingpong.py part0/results/2026-11-17/*/*.csv --out part0/results/analysis

test-analysis:
	python3 -m unittest discover -s part0/05-analysis/tests -v
