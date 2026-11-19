# Setup archive review

Eight supplied text files are preserved here as public copies. Actual network
addresses and the third node's real hostname are replaced with aliases; no
successful output was invented. The manifest records source/public hashes.
The exact original tar.gz is retained in the ignored private course records.

Three inventories and six-process hostname placement pass. Four directed SSH
checks pass; the two from heat-2 fail on unknown host keys. MPI hello fails
because the third VM cannot enter the requested checkout directory. The setup
snapshot is not ready by itself. The subsequent recheck now closes these issues;
see [the closeout record](../../../../docs/part0-closeout.md).

Run `python3 part0/05-analysis/verify_setup.py --initial-only` from the repository
root to reproduce these failures (exit 1). The default command verifies all
archives and reports the latest successful recheck (exit 0). This historical
snapshot and the unchanged 17 November ping-pong study are preserved separately.
