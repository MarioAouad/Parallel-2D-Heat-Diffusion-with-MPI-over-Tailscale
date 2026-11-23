# Run "make" at the repository root on EACH Ubuntu VM.
# mpic++ wraps the real C++ compiler with MPI headers/link libraries.
CXX := mpic++
SERIAL_CXX ?= g++
# We use the MPI C interface from C++, not the obsolete MPI C++ wrapper classes.
CPPFLAGS += -DOMPI_SKIP_MPICXX=1
# C++17 enables std::clamp; O2 optimizes; warnings help catch mistakes.
# ffp-contract=off prepares consistent arithmetic for the later heat solver.
CXXFLAGS := -std=c++17 -O2 -ffp-contract=off -Wall -Wextra -Wpedantic

.PHONY: all serial strips verify-results verify-setup analyze test-analysis check-serial verify-part1 verify-part1-results check-strips verify-part2 verify-part2-results test-part2-evidence blocks check-blocks verify-part3 verify-part3-results test-part3-evidence
all: build/mpi_hello build/mpi_pingpong build/heat build/heat_mpi build/heat_blocks

serial: build/heat

build/heat: part1/heat_serial.cpp | build
	$(SERIAL_CXX) $(CXXFLAGS) $< -o $@

# Part 2: strip-decomposed solver. Same flags as the serial reference, so the
# stencil arithmetic is identical and the output can match bit for bit.
strips: build/heat_mpi

build/heat_mpi: part2/heat_mpi.cpp | build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< -o $@

# Part 2 checks, mirroring Part 1: correctness groups on THIS VM (oversubscribed),
# the C2 study (add --cluster to span the VMs), and the offline archive check.
check-strips: build/heat build/heat_mpi
	python3 part2/verify_strips.py --exe build/heat_mpi --serial build/heat

verify-part2: build/heat build/heat_mpi
	python3 part2/run_experiments.py

verify-part2-results:
	python3 part2/verify_results.py

# Evidence-pipeline regression tests use a real serial build and a mocked MPI
# launcher. They check capture/verification, not distributed solver correctness.
test-part2-evidence:
	python3 -m unittest discover -s part2/tests -v

# Part 3: block-decomposed solver, same flags (bit-for-bit with serial), and its checks.
blocks: build/heat_blocks

build/heat_blocks: part3/heat_blocks.cpp | build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< -o $@

check-blocks: build/heat build/heat_blocks
	python3 part3/verify_blocks.py --exe build/heat_blocks --serial build/heat

# Add --cluster to span the VMs (also runs the strips-vs-blocks timing check).
verify-part3: build/heat build/heat_mpi build/heat_blocks
	python3 part3/run_experiments.py

verify-part3-results:
	python3 part3/verify_results.py

# Temporary fixtures and a mocked MPI launcher test evidence capture/validation;
# these are not distributed solver or performance measurements.
test-part3-evidence:
	python3 -m unittest discover -s part3/tests -v

# Part 4 preview is offline. Long measured campaigns require an explicit --run.
.PHONY: plan-part4 test-part4
plan-part4:
	python3 part4/run_experiments.py --plan

test-part4:
	python3 -m unittest discover -s part4/tests -v

# Final archived evidence only: no new measurements or VM access.
.PHONY: verify-part4-results verify-delivery
verify-part4-results:
	python3 part4/verify_results.py --data part4/results/2026-11-24-cluster

verify-delivery:
	python3 part0/05-analysis/verify_setup.py
	python3 part0/05-analysis/verify_results.py
	python3 part1/verify_results.py
	python3 part2/verify_results.py --data part2/results/2026-11-21-retained-cluster --require-fields
	python3 part3/verify_results.py --data part3/results/2026-11-21-retained-cluster --require-fields --require-p8
	python3 part4/verify_results.py --data part4/results/2026-11-24-cluster

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

verify-part1-results:
	python3 part1/verify_results.py

analyze:
	python3 part0/05-analysis/analyze_pingpong.py part0/results/2026-11-17/*/*.csv --out part0/results/analysis

test-analysis:
	python3 -m unittest discover -s part0/05-analysis/tests -v
