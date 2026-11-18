/*
 * Part 0, test 3: real MPI communication after the process-launch test.
 * Each process executes this SAME main function in its OWN address space.
 * mpirun creates processes; MPI_Init joins the already started processes to MPI.
 * No temperature grid is partitioned yet. A rank is a process number, not a VM.
 * Read README.md beside this file before trying the six-process run.
 */

// MPI declarations: initialization, communicators, collective operations and names.
#include <mpi.h>
// The standard C++ declaration of printf, used only for readable test output.
#include <cstdio>

int main(int argc, char** argv)
{
    // Initialize MPI before calling its communication routines.
    // Every process reaches this line; argc/argv are its command-line arguments.
    MPI_Init(&argc, &argv);

    // These variables are local to EACH process. They are not shared between VMs.
    // rank will be in [0, size-1]; size is the number of processes in the communicator.
    // name_length lets printf print exactly the processor-name characters returned.
    int rank, size, name_length;
    // Reserve the maximum hostname length promised by the MPI implementation.
    char hostname[MPI_MAX_PROCESSOR_NAME];

    // MPI_COMM_WORLD groups every process in this run. Write our own identifier
    // into rank. With -np 6, the identifiers are 0, 1, 2, 3, 4, 5.
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    // Return the communicator size, which should be six for the cluster example.
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    // Identify the VM running this process. Two ranks can report the same VM.
    // Public results call the third node heat-3; keep its existing real hostname.
    MPI_Get_processor_name(hostname, &name_length);

    // Prepare a separate local destination for the collective result.
    // The rank values 0..5 should add to 15: 6*(6-1)/2.
    int rank_sum = 0;
    // ALL ranks must call this collective in the same order. Arguments mean:
    // &rank = this process's input address; &rank_sum = its result address;
    // 1 = one integer element, NOT one byte or one network packet;
    // MPI_INT = the C++ int datatype; MPI_SUM = addition; WORLD = participants.
    // Allreduce returns the sum to EVERY rank, unlike Reduce to just one root.
    // The implementation chooses its internal algorithm/message count; six ranks
    // do not imply that exactly six low-level messages are sent. This is a functional
    // communication check, not a benchmark of Allreduce or a heat calculation.
    MPI_Allreduce(&rank, &rank_sum, 1,
                  MPI_INT, MPI_SUM, MPI_COMM_WORLD);

    // Print the local identity and collective result. Independent processes can
    // print in any order; reordered lines do not imply incorrect rank placement.
    // %.*s uses name_length to bound the hostname instead of relying on a terminator.
    std::printf("rank=%d size=%d host=%.*s rank_sum=%d\n",
                rank, size, name_length, hostname, rank_sum);

    // Release MPI resources collectively after the communication is finished.
    // Do not call ordinary MPI communication routines after Finalize.
    MPI_Finalize();
    // A zero program exit status indicates normal completion.
    return 0;
}
